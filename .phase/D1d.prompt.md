Implement Phase D1d — SSE, from docs/Jev × FHIR — Demo Technical Implementation Plan.md.

Follow AGENTS.md (standing rules: code style, tests, quality bar, real-server curls, no commits,
no checklist edits). Read .phase/progress.md first: it records what D1a–D1c built and the
deliberate choices you must build on.

Read these parts of the plan before you start:
- "Phase D1: Demo API" → "How D1 Is Organised" (the rules for every sub-phase)
- "D1 Contract (Source of Truth)": the "SSE wire format" block and its bullets, and the
  `GET /decisions/stream?limit=` row in the Step 8 table
- "#### Phase D1d — SSE": scope, the "Clarification" and "Race rule" bullets (added Sep 27),
  acceptance criteria, tests, verification, and the D1d checklist

The contract is the source of truth. If something can't work as written, stop and explain in your
report; don't redesign it. D1a–D1c are done and committed: DecisionFeed (publish / recent / since /
subscribe, subscriber_count, per-subscriber queues of 1000 that drop the oldest item),
PipelineRunner, /decisions, /pipeline/*, and /compare publishing to the feed.

## Scope (D1d only)
Add `GET /api/v1/demo/decisions/stream` to src/jev_fhir/routes/demo.py. Put the logic in a testable
async generator, e.g. in src/jev_fhir/demo/sse.py:

```python
SSE_PING_INTERVAL_S = 15.0   # module constant; tests monkeypatch it shorter

async def stream_events(
    feed: DecisionFeed, *, last_event_id: int | None, limit: int | None,
    is_disconnected: Callable[[], Awaitable[bool]],
) -> AsyncIterator[str]: ...
```

The endpoint is a thin wrapper: `StreamingResponse(stream_events(...), media_type="text/event-stream",
headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. No new dependency.

Required behaviour:
1. Wire format, byte for byte:
   `f"id: {seq}\nevent: {kind}\ndata: {event.model_dump_json()}\n\n"`, where kind is "decision" for a
   DecisionEvent and "run" for a RunEvent. A ping is exactly `": ping\n\n"`. Pings are comments and
   do NOT count toward `limit`.
2. Replay and the race rule:
   - Enter `feed.subscribe()` FIRST.
   - If last_event_id is not None, yield `feed.since(last_event_id)` in order.
   - Then yield live events, skipping any with seq ≤ the highest seq already yielded.
   - No event is lost between replay and live, and none is sent twice.
3. last_event_id comes from the `Last-Event-ID` request header. If the header is absent, the stream
   is live-only. If it's not a valid non-negative integer, ignore it and treat it as absent. A
   Last-Event-ID older than the ring buffer replays whatever the buffer still holds; that's not an
   error.
4. `limit = Query(None, ge=1)`: stop after `limit` event blocks (so 0 → 422). With no limit, the
   stream runs until the client disconnects.
5. Pings: when no event arrives within SSE_PING_INTERVAL_S, yield `": ping\n\n"`. Use
   asyncio.wait_for on the subscription's next item, or an equivalent that doesn't lose a queued
   event on timeout.
6. Disconnect: check `await is_disconnected()` on every loop iteration, including right after a ping,
   and stop when it's true.
7. Cleanup: the generator always leaves the subscription (async with), whether it ends by limit,
   disconnect, cancellation or error, so feed.subscriber_count returns to what it was. Log
   "sse_stream_closed" with the reason (limit | disconnect | cancelled) through structlog; the
   real-server check uses this log line.

Important: the app uses @app.middleware("http") (BaseHTTPMiddleware) for request-id and timing.
Verify on a REAL uvicorn process that the stream really streams (events arrive before the stream
ends) and that a client disconnect ends the generator (the "sse_stream_closed … disconnect" log
line). If BaseHTTPMiddleware breaks either, report it with evidence; don't silently restructure the
middleware.

## Tests (mock client only)
Starlette's TestClient and httpx's ASGITransport buffer a response until it ends, so an
HTTP-level stream must always end through `limit`. Test live timing and disconnect on the generator.
- tests/test_demo_sse.py (generator-level, async):
  - wire format exact for a decision block and a run block; pings match ": ping\n\n" exactly and don't
    count toward limit (monkeypatch SSE_PING_INTERVAL_S to about 0.05)
  - live delivery: subscribe, then publish from another task, then receive
  - replay: Last-Event-ID N yields only seq > N, in order, then continues live
  - race rule: events published between subscribe and replay are delivered exactly once (no gap,
    no duplicate)
  - limit ends the stream; is_disconnected → True ends it, including during ping-only idle time
  - subscriber_count returns to its prior value after limit, disconnect, and task cancellation
  - an invalid Last-Event-ID is treated as absent
- tests/test_demo_api.py (HTTP):
  - the contract test "SSE endpoint: `GET /decisions/stream?limit=3` after a pipeline run → the body
    has 3 `event:` blocks in the wire format, with `id:` lines", implemented per the plan's
    clarification: run a pipeline, wait for it to finish, then stream with `Last-Event-ID: 0` and
    `limit=3`
  - `Last-Event-ID: N` over HTTP replays only seq > N
  - run events appear as `event: run`
  - headers: content-type text/event-stream, Cache-Control no-cache, X-Accel-Buffering no
  - limit=0 → 422

## Out of scope (don't implement in D1d)
- D1e: benchmarks, static serving, CORS, the Makefile serve change (Step 10b), the OpenAPI snapshot,
  the final end-to-end checklist

## Phase-specific rules (in addition to AGENTS.md)
- Don't change the D1a–D1c contracts or behaviour (DecisionFeed, PipelineRunner, existing routes).
  All existing D1 tests must pass unchanged.
- Every stream in a test ends through limit, disconnect or a timeout.
- Coverage: src/jev_fhir/demo/sse.py ≥ 90%; the suite runtime stays reasonable.

## Verify
```
make lint && make typecheck && make test
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --port 8000
curl -s -X POST localhost:8000/api/v1/demo/pipeline/run -H 'content-type: application/json' \
  -d '{"source":"unit","rate_per_s":null}'
curl -sN -H "Last-Event-ID: 0" "localhost:8000/api/v1/demo/decisions/stream?limit=5"
curl -sN -H "Last-Event-ID: 3" "localhost:8000/api/v1/demo/decisions/stream?limit=2"
curl -sN --max-time 3 "localhost:8000/api/v1/demo/decisions/stream"   # while a paced run (rate_per_s: 2) is active:
                                                                     # events arrive live; after the timeout the log
                                                                     # shows sse_stream_closed reason=disconnect
curl -sI "localhost:8000/api/v1/demo/decisions/stream?limit=1" -H "Last-Event-ID: 0"   # headers
```

## Report back with
Everything AGENTS.md's "Final message" asks for (test count before: 389), plus:
- the output of each verification curl above
- the server log lines showing sse_stream_closed with reason=limit and reason=disconnect
