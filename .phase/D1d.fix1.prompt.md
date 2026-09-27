D1d fix-up round 1. Same rules as before (AGENTS.md and the D1d prompt). Change ONLY what is listed here.

The evaluator reproduced your D1d work: gates green, the contract and race rule correct, all real-server
curls correct, and 6/6 planted bugs caught by your tests. Budi decided the two open items:

1. **Disconnect label: ACCEPTED as-is.** `sse_stream_closed reason="cancelled"` on a real client disconnect
   (caused by BaseHTTPMiddleware) is fine. Don't change sse.py, and don't touch the middleware.

2. **Remove the extra HEAD route.** It was added only because the verification used `curl -I`. It isn't in
   the D1 contract, and the headers are verifiable through GET instead.
   - src/jev_fhir/routes/demo.py: delete the whole `@router.head("/decisions/stream", include_in_schema=False)`
     handler (`stream_decisions_headers`). Leave the GET `/decisions/stream` handler exactly as it is.
   - tests/test_demo_api.py, in `test_sse_endpoint_replays_only_events_newer_than_last_event_id_and_has_headers`:
     delete only the 3 lines that call `client.head(...)` and assert on `head`. Keep the GET header assertions
     above them (content-type, Cache-Control, X-Accel-Buffering) unchanged.

Done means:
- `rg -n "router.head|stream_decisions_headers|client.head" src tests` → no matches
- `make lint && make typecheck && make test` green; total coverage ≥ 95%; routes/demo.py ≥ 90%
- Real server, headers via GET (not HEAD):
  `curl -sN -D - -o /dev/null -H "Last-Event-ID: 0" "localhost:8000/api/v1/demo/decisions/stream?limit=1"`
  shows content-type text/event-stream, cache-control no-cache, x-accel-buffering no. Paste the output.
- No other file changed. Don't commit.

Report back with the files changed, test count before (400) → after, routes/demo.py coverage, and the pasted
curl output.
