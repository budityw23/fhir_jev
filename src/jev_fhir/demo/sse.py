"""Server-sent event streaming for the replayable demo decision feed."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Literal

from jev_fhir.demo.feed import DecisionEvent, DecisionFeed, FeedEvent
from jev_fhir.logger import get_logger

SSE_PING_INTERVAL_S = 15.0


def _event_block(seq: int, event: FeedEvent) -> str:
    """Format one feed item in the demo API's exact SSE wire format."""
    kind = "decision" if isinstance(event, DecisionEvent) else "run"
    return f"id: {seq}\nevent: {kind}\ndata: {event.model_dump_json()}\n\n"


async def stream_events(
    feed: DecisionFeed,
    *,
    last_event_id: int | None,
    limit: int | None,
    is_disconnected: Callable[[], Awaitable[bool]],
) -> AsyncIterator[str]:
    """Yield replayed and live feed events, SSE pings, and always unregister the subscriber."""
    logger = get_logger()
    reason: Literal["limit", "disconnect", "cancelled"] = "cancelled"
    yielded = 0
    # A browser can reconnect after this in-memory feed was recreated.  Its old
    # Last-Event-ID then belongs to a different feed and must not suppress new events.
    if last_event_id is not None and last_event_id > feed.last_seq:
        last_event_id = None
    highest_seq = last_event_id if last_event_id is not None else -1

    try:
        async with feed.subscribe() as subscription:
            if last_event_id is not None:
                for seq, event in feed.since(last_event_id):
                    if await is_disconnected():
                        reason = "disconnect"
                        return
                    yield _event_block(seq, event)
                    yielded += 1
                    highest_seq = seq
                    if limit is not None and yielded >= limit:
                        reason = "limit"
                        return

            while True:
                if await is_disconnected():
                    reason = "disconnect"
                    return
                if limit is not None and yielded >= limit:
                    reason = "limit"
                    return
                try:
                    seq, event = await asyncio.wait_for(
                        anext(subscription), timeout=SSE_PING_INTERVAL_S
                    )
                except TimeoutError:
                    yield ": ping\n\n"
                    continue

                if seq <= highest_seq:
                    continue
                yield _event_block(seq, event)
                yielded += 1
                highest_seq = seq
    except asyncio.CancelledError:
        reason = "disconnect" if await is_disconnected() else "cancelled"
        raise
    finally:
        logger.info("sse_stream_closed", reason=reason)
