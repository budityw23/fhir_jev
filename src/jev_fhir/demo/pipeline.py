"""Bounded background replay of labelled demo fixtures."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from jev_fhir.demo import DemoNotFoundError
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.compare import Comparer
from jev_fhir.demo.feed import DecisionEvent, DecisionFeed, RunEvent, event_from_compare
from jev_fhir.demo.schemas import CompareRequest, DemoModule, FixtureEntry, ThresholdOverrides
from jev_fhir.jev_client.client import JevClientError
from jev_fhir.logger import get_logger


class PipelineRunRequest(BaseModel):
    """What to replay: fixture source, modules, pacing, and optional threshold overrides."""

    source: Literal["all", "unit", "hard", "generated", "demo"] = "unit"
    modules: list[DemoModule] = ["quality", "router", "notifiable"]
    rate_per_s: float | None = Field(default=4.0, gt=0, le=50)
    thresholds: ThresholdOverrides | None = None


class PipelineRunResponse(BaseModel):
    """Acknowledgement of a started run; decisions arrive through the feed."""

    run_id: str
    total: int
    status: Literal["started"]


class PipelineRunner:
    """Runs one finite, paced, concurrency-bounded replay of catalog fixtures at a time."""

    def __init__(
        self, catalog: FixtureCatalog, comparer: Comparer, feed: DecisionFeed, max_concurrency: int
    ) -> None:
        self._catalog = catalog
        self._comparer = comparer
        self._feed = feed
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._task: asyncio.Task[None] | None = None
        self._active_id: str | None = None
        self._status: dict[str, str] = {}
        self._totals: dict[str, int] = {}
        self._entered: set[str] = set()

    async def start(self, request: PipelineRunRequest) -> PipelineRunResponse:
        if self._task is not None and not self._task.done():
            await self.stop(self._active_id or "")
        entries = [
            item
            for item in self._catalog.entries(
                source=None if request.source == "all" else request.source
            )
            if item.module in request.modules
        ]
        run_id = uuid4().hex
        self._active_id = run_id
        self._status[run_id] = "running"
        self._totals[run_id] = len(entries)
        self._feed.publish(
            RunEvent(run_id=run_id, status="started", total=len(entries), processed=0)
        )
        self._task = asyncio.create_task(self._run(run_id, entries, request))
        return PipelineRunResponse(run_id=run_id, total=len(entries), status="started")

    async def _run(
        self, run_id: str, entries: list[FixtureEntry], request: PipelineRunRequest
    ) -> None:
        self._entered.add(run_id)
        tasks: list[asyncio.Task[None]] = []
        processed = 0
        completed = False

        async def work(entry: FixtureEntry) -> None:
            nonlocal processed
            resource = self._catalog.load_resource(entry.id)
            async with self._semaphore:
                try:
                    response = await self._comparer.compare(
                        entry.module,
                        CompareRequest(
                            resource=resource, fixture_id=entry.id, thresholds=request.thresholds
                        ),
                    )
                    event = event_from_compare(response, run_id=run_id, fixture_id=entry.id)
                except JevClientError as exc:
                    event = DecisionEvent(
                        seq=0,
                        timestamp=datetime.now(UTC),
                        run_id=run_id,
                        fixture_id=entry.id,
                        module=entry.module,
                        resource_reference=(
                            f"{resource.get('resourceType', 'Resource')}/"
                            f"{resource.get('id', 'unknown')}"
                        ),
                        decision="error",
                        confidence=0.0,
                        lane="review",
                        lane_reason=f"jev error: {exc.error_code}",
                        latency_ms=0.0,
                        jev_latency_ms=0.0,
                        tokens_used=0,
                        ground_truth_match=None,
                        error=exc.error_code,
                    )
                self._feed.publish(event)
                processed += 1

        try:
            for index, entry in enumerate(entries):
                if index and request.rate_per_s is not None:
                    await asyncio.sleep(1 / request.rate_per_s)
                tasks.append(asyncio.create_task(work(entry)))
            await asyncio.gather(*tasks)
            completed = True
        except asyncio.CancelledError:
            await self._cancel(tasks)
            raise
        except Exception as exc:
            # Only JevClientError is an expected per-item outcome (handled in work()); anything
            # else is a bug. Stop the whole run so no sibling keeps publishing after the terminal
            # event, and record the failure instead of leaving the task exception unretrieved.
            await self._cancel(tasks)
            get_logger().error(
                "pipeline_run_failed", run_id=run_id, error=f"{type(exc).__name__}: {exc}"
            )
        finally:
            status: Literal["stopped", "finished"] = "finished" if completed else "stopped"
            self._status[run_id] = status
            self._feed.publish(
                RunEvent(run_id=run_id, status=status, total=len(entries), processed=processed)
            )
            if self._active_id == run_id:
                self._active_id = None

    async def stop(self, run_id: str) -> bool:
        if run_id not in self._status:
            raise DemoNotFoundError("pipeline run not found")
        if run_id != self._active_id or self._task is None or self._task.done():
            return False
        self._status[run_id] = "stopping"
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        if run_id not in self._entered:
            # Cancelled before _run() began, so its finally never ran: publish the terminal event
            # here so every run still gets exactly one.
            self._status[run_id] = "stopped"
            self._feed.publish(
                RunEvent(run_id=run_id, status="stopped", total=self._totals[run_id], processed=0)
            )
            if self._active_id == run_id:
                self._active_id = None
        return True

    @staticmethod
    async def _cancel(tasks: list[asyncio.Task[None]]) -> None:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def shutdown(self) -> None:
        if self._active_id is not None:
            await self.stop(self._active_id)
