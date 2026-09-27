Implement Phase D1e — Benchmarks, Static Serving, and Final Regression, from
docs/Jev × FHIR — Demo Technical Implementation Plan.md. This is the last D1 sub-phase.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: it records what D1a–D1d built and
the deliberate choices you must keep. In particular, the SSE disconnect is logged as "cancelled"
(accepted, so don't touch the middleware), and headers are checked with `curl -D -`, never `curl -I`.

Read these parts of the plan before you start:
- "Phase D1: Demo API" → "How D1 Is Organised"
- "D1 Contract (Source of Truth)": Step 8 (the `/benchmarks` rows and `BenchmarkSummary`), Step 9
  (CORS and the "Static (`demo/static.py`)" bullet), Step 10 (the Benchmarks / Static / Phase 4
  regression tests), and Step 10b (Makefile)
- "#### Phase D1e — Benchmarks, Static Serving, and Final Regression": scope, acceptance, tests,
  verification, the D1e checks, and the **Final D1 end-to-end checklist**

The contract is the source of truth. If something can't work as written, stop and explain; don't
redesign it. D1a–D1d are done and committed.

## Scope (D1e only)

### 1. Benchmarks: `src/jev_fhir/demo/benchmarks.py` (new) + routes in `routes/demo.py`
- `BenchmarkSummary` exactly as in Step 8 (name, generated_at: datetime, mode: str, dataset: str,
  jev_model: str | None).
- Report files: only files in `settings.demo_results_dir` whose name matches
  `^bench_[0-9]{8}T[0-9]{6}Z\.json$`. Ignore `.md` files and anything else.
- `list_reports(results_dir) -> list[BenchmarkSummary]`:
  - newest first, sorted by the timestamp in the file name (descending)
  - `name` is the file stem
  - `dataset` falls back to `"unit"` and `jev_model` to None when missing (pre-D0.5 reports)
  - a missing or empty directory → `[]`
  - a malformed report (bad JSON or missing `generated_at` / `mode`) is skipped with a structlog
    warning; it must not break the listing
- `load_report(results_dir, name) -> dict[str, Any]`:
  - validate `name` against `^bench_[0-9]{8}T[0-9]{6}Z$` BEFORE any filesystem access
  - the path is `results_dir / f"{name}.json"`
  - a failed regex or a missing file → `DemoNotFoundError` (→ 404 `ErrorResponse` with
    `error: "not_found"`)
  - never join any other request string onto a path
- Routes: `GET /api/v1/demo/benchmarks` → `list[BenchmarkSummary]`;
  `GET /api/v1/demo/benchmarks/{name}` → the raw report JSON.
- `POST /benchmarks/run` stays OUT of scope.

### 2. Static UI serving: `src/jev_fhir/demo/static.py` (new), wired in `main.py`
- Provide e.g. `register_static_routes(app, settings)`; call it only when `demo_enabled`. Routes are
  app-level (not under /api), with `include_in_schema=False`:
  - `GET /demo` and `GET /demo/{path:path}`
  - `GET /` → 307 redirect to `/demo`
  With demo disabled, none of these routes exist (`GET /` stays 404 as today).
- Check whether `demo_web_dist/index.html` exists **at request time**, so building the UI after
  startup works without a restart:
  - if it's missing, `/demo` and `/demo/...` return 503 through the existing `_error_response`
    helper, with `error="ui_not_built"` and `detail="run make web-build"` (the ErrorResponse shape,
    as with every other API error)
  - if it exists, resolve `(demo_web_dist / path).resolve()`. Serve it with FileResponse ONLY if
    it's a regular file AND inside `demo_web_dist.resolve()` (use `Path.is_relative_to`).
    Otherwise serve `index.html` (the SPA fallback, exactly as Step 9 says, including for
    traversal attempts). `/demo` itself serves `index.html`.
  - Symlinks that resolve outside the dist folder must not be served.

### 3. CORS in `main.py`
When `demo_enabled`, add
`CORSMiddleware(allow_origins=settings.demo_cors_origins, allow_methods=["GET","POST"], allow_headers=["*"], expose_headers=["X-Request-Id","X-Request-Duration-Ms"])`
so it's the OUTERMOST middleware (add it after the existing `@app.middleware("http")` functions).
That way a preflight OPTIONS is answered with CORS headers, and actual responses expose the two
headers. Don't add it when demo is disabled.

### 4. Makefile (Step 10b)
`serve:` becomes `$(PYTHON) -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000`. No other
Makefile change.

### 5. OpenAPI snapshot
- Add `tests/snapshots/phase4_response_schemas.json`: the `components.schemas` entries for
  `QualityScoreResponse`, `BundleRouteResponse` and `NotifiableDetectionResponse`.
- Generate it from the CURRENT code before you change anything; D1e must not change these models.
- The test compares the live `/openapi.json` of `create_app(Settings(mock_jev=True))` against the
  snapshot, with demo disabled AND enabled.
- NEVER regenerate the snapshot to make a failing test pass. If it differs, a Phase 4 contract
  changed: stop and report.

## Tests (tests/test_demo_api.py, plus unit tests for benchmarks.py / static.py if useful)
Contract tests, verbatim:
- "Benchmarks: list is sorted newest-first; a bad name → 404; a pre-D0.5 report without `dataset` →
  `"unit"`." Use a temporary `demo_results_dir` with two copied reports (one pre-D0.5 without
  `dataset`, from `benchmarks/results/bench_20260924T083443Z.json`).
- "Static: with a temp `demo_web_dist` holding `index.html` and `assets/app.js`, `/demo/studio` →
  index.html, `/demo/assets/app.js` → the file, `/demo/../../pyproject.toml` → never served."
  TestClient normalises a literal `../` before sending, so ALSO request `%2e%2e/%2e%2e/pyproject.toml`
  and `..%2f..%2fpyproject.toml`. Assert those reach the static handler and return index.html
  content, never pyproject.toml content.
- "Phase 4 regression: existing `test_api.py` passes unchanged, and the Phase 4 response schemas in
  `/openapi.json` are unchanged (snapshot compare of the three response models)."
Additional:
- `/demo` → 503 `ui_not_built` (ErrorResponse, request_id == X-Request-Id) when the dist folder is
  missing; creating `index.html` afterwards makes `/demo` serve it without a restart
- a CORS preflight (OPTIONS with `Origin: http://localhost:5173` and
  `Access-Control-Request-Method: GET`) → allowed with `access-control-allow-origin` when enabled;
  no `access-control-allow-origin` for a disallowed origin; absent when demo is disabled; an actual
  GET with an allowed Origin has `access-control-expose-headers` containing X-Request-Id
- `GET /` → 307 with `location: /demo` when enabled; 404 when disabled
- benchmarks: `.md` files ignored; a malformed report skipped; a missing directory → `[]`; a
  traversal-like or badly formatted name → 404 with no filesystem access
Use tmp_path for every results and dist folder. Never write into `benchmarks/results/` or `web/`.

## Out of scope
- `POST /benchmarks/run`; any frontend code or `web/` files (D2); any change to D1a–D1d behaviour
  or to the request-id/timing middleware.

## Phase-specific rules
- The benchmark and static code must not build filesystem paths from request strings except as
  described above (regex-validated name, contained resolved path).
- Coverage: `demo/benchmarks.py` and `demo/static.py` ≥ 90%.

## Verify
```
make lint && make typecheck && make test

MOCK_JEV=true make serve                      # demo disabled
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/demo/config    # 404
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/                      # 404
# stop it, then:
DEMO_ENABLED=true MOCK_JEV=true make serve
```
Then run the plan's **Final D1 end-to-end checklist** against this server and paste the real output
of every curl. For the stream item, use
`curl -sN -H "Last-Event-ID: 0" ".../decisions/stream?limit=5"` after the pipeline run (see the D1d
clarification). Also:
```
curl -s localhost:8000/api/v1/demo/benchmarks
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/demo/benchmarks/nope          # 404
curl -s localhost:8000/api/v1/demo/benchmarks/bench_20260924T154552Z | head -c 200
curl -s -D - -o /dev/null localhost:8000/demo                                                   # 503 ui_not_built (web/dist absent)
curl -s -D - -o /dev/null localhost:8000/                                                       # 307 → /demo
curl -s -D - -o /dev/null -X OPTIONS -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" localhost:8000/api/v1/demo/config                     # CORS preflight
```

## Report back with
Everything AGENTS.md's "Final message" asks for (test count before: 400; before D1: 342), plus the
output of every Verify curl and every Final D1 checklist curl.
