Implemented D1e.

Changed/added:
- [benchmarks.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/demo/benchmarks.py)
- [static.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/demo/static.py)
- [main.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/main.py)
- [demo.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/routes/demo.py)
- [Makefile](/home/budi/code/sphere_project/FHIR_JEV/Makefile)
- [test_demo_api.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_demo_api.py)
- [phase4_response_schemas.json](/home/budi/code/sphere_project/FHIR_JEV/tests/snapshots/phase4_response_schemas.json)

Verification passed: `make lint && make typecheck && make test`
- Tests: 400 → 407 (before D1: 342)
- Runtime: 9.04s
- Total coverage: 98%
- New modules: `demo/benchmarks.py` 100%, `demo/static.py` 100%

Real-server curl results:

```text
# demo disabled
/api/v1/demo/config -> 404
/ -> 404

# enabled config
{"mode":"mock","jev_model":null,"thresholds":{"quality_threshold":70,"route_confidence_minimum":0.5,"notifiable_confirmed":0.8,"notifiable_review":0.5},"route_options":["lab_result","encounter_summary","immunization_report","medication_dispense","unknown"],"questions":{...}}

# hard fixtures count
28

# traversal fixture request
{"error":"not_found","detail":"fixture not found",...}
404

# router compare
{'override_applied': True, 'lane': 'review', 'lane_reason': 'confidence 0.83 < floor 0.99'}

# notifiable compare
{'lane': 'flagged', 'audit_type': True, 'audit_code': False}

# pipeline
{"run_id":"42e3f8ae1a5a4d768947f18fdc032d1b","total":60,"status":"started"}

# SSE replay, limit=5
id: 1
event: decision
data: {...}

id: 2
event: run
data: {...}

id: 3
event: decision
data: {...}

id: 4
event: decision
data: {...}

id: 5
event: decision
data: {...}

# decisions
{'count': 3, 'seqs': [64, 62, 61]}

# benchmarks
[{"name":"bench_20260924T154552Z",...},{"name":"bench_20260924T151507Z",...},{"name":"bench_20260924T085042Z",...},{"name":"bench_20260924T083720Z",...},{"name":"bench_20260924T083443Z",...}]
/benchmarks/nope -> 404
/benchmarks/bench_20260924T154552Z -> {"generated_at":"2026-09-24T15:45:52.616028+00:00","mode":"mock_jev",...}

# /demo headers
HTTP/1.1 503 Service Unavailable
content-type: application/json
x-request-id: ...
x-request-duration-ms: ...
{"error":"ui_not_built","detail":"run make web-build",...}

# root headers
HTTP/1.1 307 Temporary Redirect
location: /demo

# allowed CORS preflight
HTTP/1.1 200 OK
access-control-allow-methods: GET, POST
access-control-allow-origin: http://localhost:5173

# allowed actual CORS request
access-control-expose-headers: X-Request-Id, X-Request-Duration-Ms
access-control-allow-origin: http://localhost:5173
```

Port 8000 stayed occupied by an unlisted sandbox listener after the disabled check, so enabled-mode real-server curls used a separate uvicorn process on port 8001.

No additive helpers beyond the requested static route registrar and benchmark file reader. Open question for evaluator: none.