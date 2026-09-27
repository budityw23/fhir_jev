Implemented D1d SSE.

Changed/added:
- [sse.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/demo/sse.py)
- [demo.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/routes/demo.py)
- [test_demo_sse.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_demo_sse.py)
- [test_demo_api.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_demo_api.py)

Validation:
- `make lint` ✅
- `make typecheck` ✅
- `make test` ✅ — 400 passed (389 → 400), 7.84s
- Coverage: total 98%; `demo/sse.py` 96%, `routes/demo.py` 100%.

Real-server curls:
- Pipeline POST: `{"run_id":"f19f…","total":60,"status":"started"}`
- Replay `Last-Event-ID: 0`, limit 5: emitted IDs 1–5 with `event: run` then decision blocks.
- Replay `Last-Event-ID: 3`, limit 2: emitted only IDs 4 and 5.
- Headers:
  ```text
  HTTP/1.1 200 OK
  cache-control: no-cache
  x-accel-buffering: no
  content-type: text/event-stream; charset=utf-8
  ```
- Limit-close logs:
  ```json
  {"reason":"limit","event":"sse_stream_closed",...}
  ```

Additive helper: a hidden `HEAD /decisions/stream` route supports the prescribed `curl -I` header verification without adding an OpenAPI operation.

Open question for evaluator: live streaming works—paced events arrived before `curl --max-time 3` ended—but the real server logs `sse_stream_closed` with `reason="cancelled"` rather than `"disconnect"` after curl disconnects. `request.is_disconnected()` remains false when Starlette cancels the generator under the existing `BaseHTTPMiddleware`; cleanup succeeds, but the required disconnect reason cannot be distinguished without restructuring that middleware, which the phase explicitly says not to do.