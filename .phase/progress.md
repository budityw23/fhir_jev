# Phase progress log

Running log maintained by the **evaluator** (Claude Code), not by the implementer. A few lines per
phase: what was built, deliberate choices beyond the contract, known gaps, and the verdict. Full
checklists and evaluation records live in
`docs/Jev × FHIR — Demo Technical Implementation Plan.md`.

Test count after each phase is the `make test` total.

---

## Context before D1

- **Phases 1–5** (Sep 23–24): Jev client (mock + live), FHIR serializers, three decision modules,
  FastAPI API, and a benchmark harness with rule baselines.
- **R4 fix** (`6ffd7ef`): imports switched to `fhir.resources.R4B`; the AuditEvent builder is
  R4-shaped (`type`, not `code`); 3 R5-only fixtures fixed. Verified against the official HL7 R4
  4.0.1 JSON schema.
- **D0 live readiness** (`6ab97a1`, `6cb3006`): typed Jev errors (504 / 429 / 502), SDK timeout
  and retries from Settings, thresholds from Settings, Noul `probability` = P(true) everywhere,
  `RecordingJevClient`, baselines moved to `src/jev_fhir/baselines/`, banded quality labels,
  `bench-live` and `smoke-live`.
  - Deliberate choice: the NIK check **gates** quality auto-accept (`score ≥ threshold` AND
    `nik_valid is not False`) in `QualityScorer` and in the rule baseline (Budi's decision).
    `QualityLabel` rejects band/action/NIK contradictions.
- **D0.5 benchmark dataset** (`e977ee6`): 204 labelled fixtures (unit / hard / generated / demo),
  a deterministic generator, `--dataset full` breakdowns. Evaluation fixes: demo JE coded `A83.0`
  (was `A83`); generated encounter bundles link their Conditions to the Encounter.
  - Known gaps (⚠️, non-blocking): generator defects are round-robin, not RNG-picked;
    valid-NIK generated patients are labelled `expected_nik_valid: null`; `urn:uuid` fullUrls
    aren't real UUIDs.
  - Pending (Budi): approve the hard and quality labels (`approved_by: null`); Open Questions 9
    (notifiable scope A00–A09 vs A00/A01) and 10 (vitals-only bundle label); a committed live full
    benchmark report; rotate the old Jev key.
- **D1 split** (`b0ccfa1`): D1 is built as D1a → D1e against a verbatim contract. The 404 body
  decision (`f5cf909`): demo not-found errors use `ErrorResponse` via `DemoNotFoundError`; no
  global HTTPException handler, so unknown routes keep FastAPI's default 404.

---

## D1a — Foundations — PASS (Sep 25, 2026) — `c0b54fc`

- **Built:**
  - demo settings (`demo_enabled`, `demo_pipeline_max_concurrency`, `demo_cors_origins`,
    `demo_results_dir`, `demo_web_dist`)
  - `demo/schemas.py` (all Step 2 models)
  - `FixtureCatalog`: an allow-list from the labels; `load_resource` never touches the filesystem
    for unknown ids
  - `DemoServices(catalog)` and the demo router, both mounted only when `DEMO_ENABLED=true`
- **Choices beyond the contract:**
  - `FixtureEntry.label` shows `· NIK ✓` / `· NIK ✗` / nothing
  - `ground_truth` is dumped with `mode="json"`, so bands are lists
- **Evaluation fixes:**
  - `ground_truth` now keeps `rationale` and `approved_by`
  - `entries()` uses the contract types
  - catalog tests read counts and approvals from the label files, so they survive label approval
- Tests 342 → 353. Known gaps: none.

## D1b — Compare API — PASS (Sep 27, 2026) — `f781f39`

- **Built:**
  - `lanes.assign_lane` (9 exact reason strings, including `NIK gate failed: P(valid) {p:.2f}`)
  - `Comparer` (a fresh `RecordingJevClient` and fresh modules per call; rule decisions with the
    NIK gate and `score_observation`; verdicts; R4 audit event; tokens)
  - `/config`, `/fixtures`, `/fixtures/{id}`, `/compare/{module}`
- **Choices beyond the contract:**
  - `DemoNotFoundError` → 404 `ErrorResponse`
  - an unknown `fixture_id` in a compare is **not** an error (ground truth and verdict are null)
  - AuditEvent `module_name` is `quality_scorer` / `bundle_router` / `notifiable_detector`
  - quality lane check order: auto_accept → score < threshold → NIK gate
- **Evaluation fixes:**
  - the missing contract tests were added: traversal, Observation compare, NIK-gated patient
  - the concurrency test made meaningful
  - the runtime `assert` replaced by `TypeError`
  - schema docstrings added
- **Test note:** TestClient normalises a literal `../` before sending, so traversal must also be
  tested with percent-encoded forms (`%2e%2e`, `..%2f`).
- Tests 353 → 369. Known gaps: none.

## D1c — Feed and Pipeline — PASS (Sep 27, 2026) — `10d656c`

- **Built:**
  - `DecisionFeed`: ring buffer 500, `seq` stamped on publish, `recent` / `since`, `subscribe()`
    with per-subscriber queues (1000) that drop only that subscriber's oldest item
  - `PipelineRunner`: one run at a time, paced launches, semaphore concurrency, `JevClientError`
    → review event
  - `/decisions`, `/pipeline/run`, `/pipeline/{id}/stop`; `/compare` publishes; lifespan
    shutdown stops the active run
- **Choices beyond the contract:**
  - `subscriber_count` property (for D1d's leak checks)
  - `event_from_compare`: the single compare → event mapping
  - stopping a known finished run returns `{"stopped": false}`; an unknown run → 404
  - exactly one terminal RunEvent through `try/finally`
  - any unexpected item exception stops the whole run ("stopped", siblings cancelled, logged as
    `pipeline_run_failed`)
  - `stop()` publishes "stopped" itself for a run cancelled before `_run()` began (no
    `sleep(0)` reliance)
- **Evaluation fixes:** the unexpected-exception path (previously published "finished" while
  siblings kept publishing), the start/stop race, and docstrings.
- Tests 369 → 389. Known gaps: none.

## Pre-D1d note (Sep 27, 2026) — `4f7eea3`

- SSE is live-only without `Last-Event-ID`. A stream opened after a finished run needs
  `Last-Event-ID: 0` to replay; otherwise it only gets pings. Race rule: subscribe first, then
  replay, then drop live events with `seq ≤` the last replayed one.

## D1d — SSE — PASS (Sep 27, 2026) — first /phase-loop run (Codex headless, 1 fix-up round)

- **Built:**
  - `demo/sse.py` `stream_events()` generator, with `SSE_PING_INTERVAL_S = 15.0` as a module constant
  - `GET /decisions/stream?limit=`: `StreamingResponse`, `text/event-stream`, `Cache-Control: no-cache`,
    `X-Accel-Buffering: no`
  - exact `id / event / data` blocks and `": ping"` comments that don't count toward `limit`
  - `Last-Event-ID` replay; subscribe BEFORE replay, then drop live `seq ≤` the last one sent; `sse_stream_closed`
    logged with the reason
- **Choices beyond the contract:**
  - the logic lives in a testable generator (TestClient buffers streams)
  - an invalid `Last-Event-ID` is ignored (treated as absent)
  - `limit` has `ge=1` (0 → 422)
  - the log reason is `limit` / `disconnect` / `cancelled`
- **Accepted deviation (Budi):** a real client disconnect logs `reason="cancelled"`, not `"disconnect"`. The app's
  `BaseHTTPMiddleware` cancels the generator before `is_disconnected()` turns true. Cleanup is correct; only the
  label differs. Don't "fix" this by restructuring the middleware without asking.
- **Fix-up:** Codex had added a hidden HEAD route because the prompt used `curl -I`. Removed. **Lesson for future
  prompts:** check headers with `curl -D - -o /dev/null`, never `curl -I` (FastAPI doesn't add HEAD for GET routes).
- Tests 389 → 400. Known gaps: `sse.py` lines 37–38 (disconnect during replay) untested (96% coverage).

## D1e — Benchmarks, static serving, final D1 regression — PASS (Sep 27, 2026) — /phase-loop, 2 fix-up rounds (tests only)

- **Built:**
  - `demo/benchmarks.py`: `BenchmarkSummary`, `list_reports()` (only `bench_*Z.json`, newest first by filename, `dataset`
    → "unit" and `jev_model` → null for old reports, malformed reports skipped with a warning, missing dir → `[]`),
    `load_report()` (regex-validated before any file access → 404)
  - `/benchmarks`, `/benchmarks/{name}`
  - `demo/static.py`: `/demo`, `/demo/{path}`, `/` → 307 `/demo` (demo mode only); UI presence checked PER REQUEST
    (503 `ui_not_built` until `web/dist/index.html` exists); files served only when the resolved path is inside the dist
    folder, otherwise the `index.html` SPA fallback
  - CORS (outermost, demo only); `make serve` via `$(PYTHON)`
  - `tests/snapshots/phase4_response_schemas.json`, a snapshot of the three Phase 4 response models
- **Choices beyond the contract:** the 503 uses the ErrorResponse shape (error + detail + request_id + timestamp); static
  routes are hidden from OpenAPI; a traversal gets the SPA fallback (per the contract), not 404.
- **Fix-ups:** two tests passed with their security check removed (static containment: targets didn't exist; name regex:
  the directory was missing), so real secret files and a read_text patch were added. Round 2 restored 3 assertions round 1
  had dropped. **Lessons for future prompts:**
  - a "never serves X" test must make X actually exist and be reachable
  - when strengthening a test, don't drop its old assertions (split into a new test instead)
- **Known gaps (⚠️):**
  - an explicit `"dataset": null` report is skipped (not defaulted)
  - loading a malformed report via `/benchmarks/{name}` → 400
- **Evaluator note:** `make serve` spawns uvicorn as a child, so killing make leaves the server running. Kill by PID from
  `ss -ltnp` (not `ps | grep` or `pkill -f` on a pattern present in your own command line).
- Tests 400 → 408 (D1 total: 342 → 408). **D1 complete.** Next: D2 (web UI; Node via nvm).
