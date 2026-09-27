"""D1d generator-level server-sent event tests."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from jev_fhir.demo import sse
from jev_fhir.demo.feed import DecisionEvent, DecisionFeed, RunEvent


def decision(index: int = 0) -> DecisionEvent:
    """Build a small deterministic decision event for SSE tests."""
    return DecisionEvent(
        seq=index,
        timestamp=datetime(2026, 9, 27, tzinfo=UTC),
        run_id="run-1",
        fixture_id="fixture.json",
        module="quality",
        resource_reference="Patient/patient-1",
        decision="auto_accept",
        confidence=0.9,
        lane="auto_accepted",
        lane_reason="score 90 ≥ threshold 70",
        latency_ms=1.0,
        jev_latency_ms=0.5,
        tokens_used=3,
        ground_truth_match=True,
    )


async def connected() -> bool:
    """Report that a test client remains connected."""
    return False


@pytest.mark.asyncio
async def test_stream_events_formats_decision_and_run_blocks_exactly() -> None:
    feed = DecisionFeed()
    feed.publish(decision())
    feed.publish(RunEvent(run_id="run-1", status="finished", total=1, processed=1))
    events = sse.stream_events(feed, last_event_id=0, limit=2, is_disconnected=connected)

    decision_block = await anext(events)
    run_block = await anext(events)

    expected_decision = f"id: 1\nevent: decision\ndata: {feed.since(0)[0][1].model_dump_json()}\n\n"
    assert decision_block == expected_decision
    assert run_block == f"id: 2\nevent: run\ndata: {feed.since(0)[1][1].model_dump_json()}\n\n"
    with pytest.raises(StopAsyncIteration):
        await anext(events)
    assert feed.subscriber_count == 0


@pytest.mark.asyncio
async def test_stream_events_ping_is_exact_and_does_not_count_toward_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sse, "SSE_PING_INTERVAL_S", 0.01)
    feed = DecisionFeed()
    events = sse.stream_events(feed, last_event_id=None, limit=1, is_disconnected=connected)

    assert await anext(events) == ": ping\n\n"
    feed.publish(decision())
    assert (await anext(events)).startswith("id: 1\nevent: decision\n")
    with pytest.raises(StopAsyncIteration):
        await anext(events)


@pytest.mark.asyncio
async def test_stream_events_delivers_a_live_event_after_subscription() -> None:
    feed = DecisionFeed()
    events = sse.stream_events(feed, last_event_id=None, limit=1, is_disconnected=connected)

    async def receive() -> str:
        return await anext(events)

    next_event: asyncio.Task[str] = asyncio.create_task(receive())
    await asyncio.sleep(0)
    assert feed.subscriber_count == 1
    feed.publish(decision())

    assert (await asyncio.wait_for(next_event, timeout=0.2)).startswith("id: 1\nevent: decision\n")
    with pytest.raises(StopAsyncIteration):
        await anext(events)
    assert feed.subscriber_count == 0


@pytest.mark.asyncio
async def test_stream_events_replays_only_newer_events_then_continues_live() -> None:
    feed = DecisionFeed()
    for index in range(3):
        feed.publish(decision(index))
    events = sse.stream_events(feed, last_event_id=1, limit=3, is_disconnected=connected)

    assert (await anext(events)).startswith("id: 2\n")
    assert (await anext(events)).startswith("id: 3\n")
    feed.publish(decision(3))
    assert (await anext(events)).startswith("id: 4\n")
    with pytest.raises(StopAsyncIteration):
        await anext(events)


@pytest.mark.asyncio
async def test_stream_events_race_replays_and_live_queue_without_gap_or_duplicate() -> None:
    class RacingFeed(DecisionFeed):
        """Publish on either side of the replay snapshot while a subscriber is registered."""

        def since(self, seq: int) -> list[tuple[int, DecisionEvent | RunEvent]]:
            self.publish(decision(2))
            replay = super().since(seq)
            self.publish(decision(3))
            return replay

    feed = RacingFeed()
    feed.publish(decision(1))
    events = sse.stream_events(feed, last_event_id=0, limit=3, is_disconnected=connected)

    blocks = [await anext(events) for _ in range(3)]
    assert [block.splitlines()[0] for block in blocks] == ["id: 1", "id: 2", "id: 3"]
    with pytest.raises(StopAsyncIteration):
        await anext(events)


@pytest.mark.asyncio
async def test_stream_events_disconnects_during_ping_idle_time_and_unregisters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sse, "SSE_PING_INTERVAL_S", 0.01)
    checks = iter([False, True])

    async def disconnect_after_ping() -> bool:
        return next(checks)

    feed = DecisionFeed()
    events = sse.stream_events(
        feed, last_event_id=None, limit=None, is_disconnected=disconnect_after_ping
    )
    assert await anext(events) == ": ping\n\n"
    with pytest.raises(StopAsyncIteration):
        await anext(events)
    assert feed.subscriber_count == 0


@pytest.mark.asyncio
async def test_stream_events_unregisters_after_task_cancellation() -> None:
    feed = DecisionFeed()
    events: AsyncIterator[str] = sse.stream_events(
        feed, last_event_id=None, limit=None, is_disconnected=connected
    )

    async def receive() -> str:
        return await anext(events)

    task: asyncio.Task[str] = asyncio.create_task(receive())
    await asyncio.sleep(0)
    assert feed.subscriber_count == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert feed.subscriber_count == 0
