"""In-memory, replayable decision feed for the demo API."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime
from typing import Literal, cast

from pydantic import BaseModel

from jev_fhir.demo.schemas import CompareResponse, DemoModule, Lane
from jev_fhir.modules.bundle_router import BundleRouteResponse
from jev_fhir.modules.notifiable_detector import NotifiableDetectionResponse
from jev_fhir.modules.quality_scorer import QualityScoreResponse


class DecisionEvent(BaseModel):
    """One demo decision as published to the feed; seq is stamped by DecisionFeed.publish."""

    seq: int
    timestamp: datetime
    run_id: str | None
    fixture_id: str | None
    module: DemoModule
    resource_reference: str
    decision: str
    confidence: float
    lane: Lane
    lane_reason: str
    latency_ms: float
    jev_latency_ms: float
    tokens_used: int
    ground_truth_match: bool | None
    error: str | None = None


class RunEvent(BaseModel):
    """A pipeline run lifecycle event: started, then exactly one of finished or stopped."""

    run_id: str
    status: Literal["started", "finished", "stopped"]
    total: int
    processed: int


FeedEvent = DecisionEvent | RunEvent


class Subscription:
    """A live view of the feed: async context manager and async iterator of (seq, event)."""

    def __init__(self, feed: DecisionFeed) -> None:
        self._feed = feed
        self._queue: asyncio.Queue[tuple[int, FeedEvent]] = asyncio.Queue(maxsize=1000)

    async def __aenter__(self) -> Subscription:
        self._feed._subscribers.append(self._queue)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._queue in self._feed._subscribers:
            self._feed._subscribers.remove(self._queue)

    def __aiter__(self) -> Subscription:
        return self

    async def __anext__(self) -> tuple[int, FeedEvent]:
        return await self._queue.get()


class DecisionFeed:
    """Ring-buffered event feed with sequence numbers, replay, and per-subscriber queues."""

    def __init__(self, maxlen: int = 500) -> None:
        self._sequence = 0
        self._events: deque[tuple[int, FeedEvent]] = deque(maxlen=maxlen)
        self._subscribers: list[asyncio.Queue[tuple[int, FeedEvent]]] = []

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def last_seq(self) -> int:
        """Return the highest sequence number issued by this feed, or zero when empty."""
        return self._sequence

    def publish(self, event: FeedEvent) -> int:
        self._sequence += 1
        seq = self._sequence
        stamped = (
            event.model_copy(update={"seq": seq}) if isinstance(event, DecisionEvent) else event
        )
        item = (seq, stamped)
        self._events.append(item)
        for queue in self._subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(item)
        return seq

    def recent(self, limit: int = 50) -> list[DecisionEvent]:
        return [event for _, event in reversed(self._events) if isinstance(event, DecisionEvent)][
            :limit
        ]

    def since(self, seq: int) -> list[tuple[int, FeedEvent]]:
        return [item for item in self._events if item[0] > seq]

    def subscribe(self) -> Subscription:
        return Subscription(self)


def event_from_compare(
    response: CompareResponse, *, run_id: str | None, fixture_id: str | None
) -> DecisionEvent:
    """Map a compare result to its feed event; the single mapping used by /compare and pipelines."""
    entity = cast(dict[str, object], response.audit_event["entity"][0])
    what = cast(dict[str, str], entity["what"])
    jev = response.jev
    if response.module == "notifiable":
        confidence = cast(NotifiableDetectionResponse, jev).probability
    else:
        confidence = cast(QualityScoreResponse | BundleRouteResponse, jev).confidence
    return DecisionEvent(
        seq=0,
        timestamp=datetime.now(UTC),
        run_id=run_id,
        fixture_id=fixture_id,
        module=response.module,
        resource_reference=what["reference"],
        decision=response.jev_decision,
        confidence=confidence,
        lane=response.lane,
        lane_reason=response.lane_reason,
        latency_ms=jev.latency_ms,
        jev_latency_ms=sum(call.result.latency_ms for call in response.jev_raw),
        tokens_used=response.tokens_used,
        ground_truth_match=response.verdict.jev_correct,
    )
