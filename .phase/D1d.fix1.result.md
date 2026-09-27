Removed the non-contract HEAD route and its three HTTP-test assertions.

Changed:
- `src/jev_fhir/routes/demo.py`
- `tests/test_demo_api.py`

Verification:
- `rg -n "router.head|stream_decisions_headers|client.head" src tests` → no matches
- `make lint && make typecheck && make test` → green
- Tests: 400 → 400 passed in 7.80s
- `routes/demo.py` coverage: 100%
- Total coverage: 98%

Real-server GET header output:

```http
HTTP/1.1 200 OK
date: Sun, 27 Sep 2026 02:54:59 GMT
server: uvicorn
cache-control: no-cache
x-accel-buffering: no
content-type: text/event-stream; charset=utf-8
x-request-id: a5f88045-e294-4d10-b5cd-606b3726999b
x-request-duration-ms: 8.657
transfer-encoding: chunked
```

No commit made.