"""D1c pipeline lifecycle tests using only mock Jev clients."""

import asyncio
from pathlib import Path
from time import monotonic
from typing import Any

import pytest

from jev_fhir.config import Settings
from jev_fhir.demo import DemoNotFoundError
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.compare import Comparer
from jev_fhir.demo.feed import DecisionEvent, DecisionFeed, RunEvent
from jev_fhir.demo.pipeline import PipelineRunner, PipelineRunRequest
from jev_fhir.demo.schemas import CompareRequest, CompareResponse, DemoModule, Thresholds
from jev_fhir.jev_client.client import JevTimeoutError
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.jev_client.models import ChoiceResult

ROOT = Path(__file__).resolve().parents[1]


def make_runner(
    client: MockJevClient | None = None, concurrency: int = 4
) -> tuple[PipelineRunner, DecisionFeed]:
    catalog = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    feed = DecisionFeed()
    return (
        PipelineRunner(
            catalog,
            Comparer(
                client or MockJevClient(),
                catalog,
                Thresholds.from_settings(Settings()),
                ROOT / "data/notifiable_diseases.json",
            ),
            feed,
            concurrency,
        ),
        feed,
    )


async def wait_for_terminal(feed: DecisionFeed, run_id: str) -> RunEvent:
    for _ in range(300):
        for _, event in feed.since(0):
            if isinstance(event, RunEvent) and event.run_id == run_id and event.status != "started":
                return event
        await asyncio.sleep(0.01)
    raise AssertionError("pipeline did not reach a terminal event")


@pytest.mark.asyncio
async def test_unit_pipeline_finishes_with_all_decisions() -> None:
    runner, feed = make_runner()
    started = await runner.start(PipelineRunRequest(source="unit", rate_per_s=None))
    terminal = await wait_for_terminal(feed, started.run_id)
    decisions = [
        event
        for event in feed.recent(500)
        if event.run_id == started.run_id and isinstance(event, DecisionEvent)
    ]
    assert len(decisions) == started.total
    assert terminal.status == "finished" and terminal.processed == started.total
    assert [
        event.status
        for _, event in feed.since(0)
        if isinstance(event, RunEvent) and event.run_id == started.run_id
    ] == ["started", "finished"]
    assert await runner.stop(started.run_id) is False
    with pytest.raises(DemoNotFoundError):
        await runner.stop("missing")


@pytest.mark.asyncio
async def test_second_start_stops_the_first_run_once() -> None:
    runner, feed = make_runner()
    first = await runner.start(PipelineRunRequest(source="unit", modules=["router"], rate_per_s=1))
    second = await runner.start(
        PipelineRunRequest(source="demo", modules=["router"], rate_per_s=None)
    )
    assert (await wait_for_terminal(feed, first.run_id)).status == "stopped"
    assert (await wait_for_terminal(feed, second.run_id)).status == "finished"
    assert (
        len(
            [
                event
                for _, event in feed.since(0)
                if isinstance(event, RunEvent)
                and event.run_id == first.run_id
                and event.status == "stopped"
            ]
        )
        == 1
    )


class TimeoutOnceComparer:
    def __init__(self, wrapped: Comparer) -> None:
        self._wrapped = wrapped
        self._raised = False

    async def compare(self, module: DemoModule, request: CompareRequest) -> CompareResponse:
        if not self._raised:
            self._raised = True
            raise JevTimeoutError("injected")
        return await self._wrapped.compare(module, request)


@pytest.mark.asyncio
async def test_jev_timeout_becomes_review_event_and_run_continues() -> None:
    runner, feed = make_runner()
    runner._comparer = TimeoutOnceComparer(runner._comparer)  # type: ignore[assignment]
    started = await runner.start(
        PipelineRunRequest(source="demo", modules=["router"], rate_per_s=None)
    )
    assert (await wait_for_terminal(feed, started.run_id)).status == "finished"
    errors = [
        event
        for event in feed.recent(500)
        if event.run_id == started.run_id and event.error == "jev_timeout"
    ]
    assert len(errors) == 1
    assert errors[0].lane == "review" and errors[0].decision == "error"


@pytest.mark.asyncio
async def test_stop_cancels_inflight_tasks_without_late_events() -> None:
    runner, feed = make_runner()
    started = await runner.start(
        PipelineRunRequest(source="unit", modules=["router"], rate_per_s=1)
    )
    await asyncio.sleep(0.01)
    assert await runner.stop(started.run_id) is True
    terminal = await wait_for_terminal(feed, started.run_id)
    assert terminal.status == "stopped"
    after_stop = len([event for event in feed.recent(500) if event.run_id == started.run_id])
    await asyncio.sleep(0.08)
    assert (
        len([event for event in feed.recent(500) if event.run_id == started.run_id]) == after_stop
    )


@pytest.mark.asyncio
async def test_shutdown_stops_active_run() -> None:
    runner, feed = make_runner()
    started = await runner.start(
        PipelineRunRequest(source="unit", modules=["router"], rate_per_s=1)
    )
    await asyncio.sleep(0.01)
    await runner.shutdown()
    assert (await wait_for_terminal(feed, started.run_id)).status == "stopped"


@pytest.mark.asyncio
async def test_pacing_waits_between_launches() -> None:
    runner, feed = make_runner()
    started_at = monotonic()
    started = await runner.start(
        PipelineRunRequest(source="demo", modules=["router"], rate_per_s=20)
    )
    await wait_for_terminal(feed, started.run_id)
    assert monotonic() - started_at >= (started.total - 1) / 20


class CountingMockJevClient(MockJevClient):
    def __init__(self) -> None:
        self.inflight = 0
        self.max_inflight = 0

    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            await asyncio.sleep(0.01)
            return await super().choice(state, question, options)
        finally:
            self.inflight -= 1


@pytest.mark.asyncio
async def test_pipeline_concurrency_never_exceeds_configured_limit() -> None:
    client = CountingMockJevClient()
    runner, feed = make_runner(client, concurrency=2)
    started = await runner.start(
        PipelineRunRequest(source="unit", modules=["router"], rate_per_s=None)
    )
    assert (await wait_for_terminal(feed, started.run_id)).status == "finished"
    assert client.max_inflight == 2


class FailFirstComparer:
    """Raises an unexpected (non-Jev) error on the first item while siblings are still in flight."""

    def __init__(self, wrapped: Comparer) -> None:
        self._wrapped = wrapped
        self._failed = False

    async def compare(self, module: DemoModule, request: CompareRequest) -> CompareResponse:
        if not self._failed:
            self._failed = True
            raise ValueError("unexpected bug in one item")
        await asyncio.sleep(0.05)
        return await self._wrapped.compare(module, request)


@pytest.mark.asyncio
async def test_unexpected_item_error_stops_run_without_orphaned_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner, feed = make_runner()
    runner._comparer = FailFirstComparer(runner._comparer)  # type: ignore[assignment]
    started = await runner.start(
        PipelineRunRequest(source="unit", modules=["router"], rate_per_s=None)
    )
    terminal = await wait_for_terminal(feed, started.run_id)
    await asyncio.sleep(0.2)  # siblings would have finished by now if they were still running
    events = [
        (seq, event)
        for seq, event in feed.since(0)
        if getattr(event, "run_id", None) == started.run_id
    ]
    terminals = [(seq, e) for seq, e in events if isinstance(e, RunEvent) and e.status != "started"]
    assert len(terminals) == 1
    terminal_seq, terminal_event = terminals[0]
    assert terminal is terminal_event and terminal.status == "stopped"
    assert terminal.processed < started.total
    assert not [seq for seq, e in events if isinstance(e, DecisionEvent) and seq > terminal_seq]
    assert runner._task is not None and runner._task.exception() is None
    assert "pipeline_run_failed" in capsys.readouterr().out
    assert await runner.stop(started.run_id) is False


@pytest.mark.asyncio
async def test_stop_before_the_run_starts_still_emits_one_stopped_event() -> None:
    runner, feed = make_runner()
    started = await runner.start(
        PipelineRunRequest(source="unit", modules=["router"], rate_per_s=None)
    )
    assert await runner.stop(started.run_id) is True  # no await between start and stop
    run_events = [
        event
        for _, event in feed.since(0)
        if isinstance(event, RunEvent) and event.run_id == started.run_id
    ]
    assert [event.status for event in run_events] == ["started", "stopped"]
    assert run_events[-1].processed == 0
    assert not [e for e in feed.recent(500) if e.run_id == started.run_id]
    follow_up = await runner.start(
        PipelineRunRequest(source="demo", modules=["router"], rate_per_s=None)
    )
    assert (await wait_for_terminal(feed, follow_up.run_id)).status == "finished"
