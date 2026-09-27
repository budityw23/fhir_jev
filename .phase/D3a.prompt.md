Implement Phase D3a — Live Pipeline screen (+ SSE restart fix), from
docs/Jev × FHIR — Demo Technical Implementation Plan.md.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2a–D2c built the web foundations, the Overview, Studio
and Playground; reuse their components (`LaneChip`, `ThresholdSliders`, `ErrorCard`), `api()` in `web/src/api/client.ts`,
the TanStack Query hooks, `web/src/lib/format.ts`, and the e2e network guard in `web/e2e/fixtures.ts`. Keep the D2 lessons:
- never obfuscate data to pass a check
- every test must fail when the behaviour it names is removed (the evaluator plants bugs)
- lines ≤ 100 chars; ESLint `max-len` must keep covering JSX, so don't re-add `ignoreStrings` / `ignoreTemplateLiterals`
- render the backend's explanation fields (`lane`, `lane_reason`) exactly as sent
- the evaluator LOOKS at the screenshots: layout must be readable (spaced, labelled, no run-together text)

Read before you start:
- the plan: "## Phase D3" → "How D3 Is Organised" (incl. "Decisions and clarifications"), the "D3 Contract" Steps 1–3 and 5,
  and "#### Phase D3a" (scope, tests, checklist)
- docs/Jev × FHIR — Demo Plan Requirement.md §3 UI-P-1…7 and UI-NFR-1

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies (Recharts is already
installed). No backend change beyond the SSE rule below.

## Scope (D3a only)

### 1. Backend: SSE restart rule (`src/jev_fhir/demo/sse.py`)
The feed is in memory, so a server restart resets `seq` to 1, while a reconnecting browser resends its old
`Last-Event-ID` (e.g. 812). Today `stream_events` then replays nothing and drops every live event with `seq ≤ 812`.
- Rule: **if `last_event_id` is greater than the highest `seq` the feed has issued, treat it as absent** (no replay,
  `highest_seq` starts at -1, every live event is delivered).
- `last_event_id` equal to or below the highest issued seq keeps today's behaviour exactly.
- "Highest issued seq" is the feed's counter (0 when nothing was ever published), not the lowest seq still in the ring
  buffer. You may add ONE read-only property to `DecisionFeed` in `src/jev_fhir/demo/feed.py` (e.g. `last_seq`, with a
  docstring) for this; no other change to `feed.py`, and no other backend file.
- Tests in `tests/test_demo_sse.py` (existing tests unchanged):
  - a feed that issued 3 events, `last_event_id=812` → a live event published after subscribing (seq 4) IS delivered,
    and nothing is replayed
  - an empty feed (a restarted server), `last_event_id=5` → the first live event (seq 1) is delivered
  - `last_event_id` equal to the highest issued seq → no replay; the next live event is delivered (unchanged behaviour)
  - removing the rule must make a test fail; each test ends by `limit`, never hangs

### 2. `web/src/api/sse.ts` (Step 1, signatures exactly as in the contract)
- `RunEvent` is NOT in the OpenAPI schema (it's only sent over SSE). Add a hand-written `RunEvent` interface to
  `web/src/api/types.ts` next to `ErrorBody`, with a comment, mirroring `src/jev_fhir/demo/feed.py` exactly:
  `{ run_id: string; status: "started" | "finished" | "stopped"; total: number; processed: number }`.
  `DecisionEvent`, `Lane` etc. still come from the generated schema.
- Native `EventSource("/api/v1/demo/decisions/stream")`, listeners for `decision` and `run`; parse `data` as JSON and
  `seq` from `lastEventId` (a number). `connected` becomes true on `onopen` and false on `onerror`. Close on unmount.
- Keep the latest `onEvent` in a ref so re-renders don't reopen the connection.

### 3. `web/src/pages/pipeline/reducer.ts` (Step 2, pure, types exactly as in the contract)
- `run: started` with a new `run_id`: `current` (if any) moves to `previous`; a fresh `RunSummary` starts
  (`total` from the event, `processed` 0, status "running", all four lanes 0); `events`, `latencies`, `confidences` reset.
- A `decision` or `run` event whose `run_id` isn't `current.runId` (including `null` run ids from `/compare`, and any
  event while `current` is null) is ignored.
- A decision for the current run: `processed` +1; its lane +1; when `lane === "routed"`, `routedByCategory[decision]` +1;
  `agreement.judged` +1 when `ground_truth_match !== null`, `agreement.correct` +1 when it's `true`; `tokens` +=
  `tokens_used`; `errors` +1 when `error` is non-null; the event is prepended to `events` (newest first, cap 500);
  `jev_latency_ms` appended to `latencies` (keep the last 50); `confidence` appended to `confidences`.
- `run: finished` / `run: stopped` for the current run sets the status (and `processed` from the event if larger).
- `reset` returns the initial state.

### 4. Pipeline page (Step 3): replace the `/pipeline` placeholder in `web/src/App.tsx`
Put the page in `web/src/pages/Pipeline.tsx` and the components in `web/src/components/pipeline/`. The reducer is fed by
`useDecisionStream`. Each component gets a stable `data-testid`.
- **RunControls:** source select (`all`, `unit`, `hard`, `generated`, `demo`; default `unit`); pace 1 / 4 / 10 / max
  (→ `rate_per_s` 1, 4, 10, `null`); one D2b `ThresholdSliders` per module (quality, router, notifiable), props unchanged,
  initialised from `useDemoConfig()` thresholds. Start → `POST /api/v1/demo/pipeline/run` with
  `{ source, modules: all three, rate_per_s, thresholds }` (send `thresholds` only for values changed from the config
  defaults, as the Studio does, or the full object; say which in your report). Stop → `POST /pipeline/{run_id}/stop` for
  the current run (disabled when nothing is running). Reset → dispatch `reset`. API failures render `ErrorCard`.
  Show the run status text ("running" / "finished" / "stopped") with `data-testid="run-status"`.
- **StatsStrip:** processed/total; throughput = decision events whose `timestamp` is within 5 s of the NEWEST event's
  timestamp, divided by 5 (deterministic, testable); p50/p95 of `latencies` (nearest-rank; say which in the report);
  agreement % = correct / judged (show "—" when judged is 0); tokens; cost = tokens × 42 / 1e9 USD shown ONLY when
  `useHealth().jev_client === "live"`.
- **LaneBoard:** four columns (auto_accepted, routed, flagged, review) with counters (`data-testid="lane-count-<lane>"`);
  Routed shows sub-counts per category; each column lists its last 8 items. Colour always paired with icon + text
  (reuse `LaneChip` styling).
- **LiveFeed:** table with time, ref (`resource_reference`), module, decision, confidence bar, latency, lane chip;
  renders at most **100** rows (slice `events`); a row click navigates to `/studio/{module}?fixture={fixture_id}`
  (router navigation, respecting the `/demo` basename).
- **LatencySparkline:** Recharts line of the last 50 latencies. **ConfidenceHistogram:** 10 buckets (0–0.1 … 0.9–1.0,
  1.0 in the last bucket), stacked by module. Both update through a `requestAnimationFrame` throttle (at most one chart
  update per frame, cancelled on unmount).
- **ReviewQueue:** the current run's `review`-lane items, each with its resource ref, module and its **exact**
  `lane_reason`. A review item is clickable/expandable and shows its `lane_reason` (`data-testid="review-reason"`).
  Accept / Override buttons change **client state only** (no fetch), with the visible label "simulated reviewer".
- **RerunDelta:** only when `previous` exists: `Review queue: {prev} → {curr} (Δ ±n)` using the review lane counts;
  the sign is explicit (`+3`, `−2` or `-2`, `±0` or `0`; state your choice in the report).

### 5. Screenshots
Add the Pipeline page after a finished `unit` run at max pace to the screenshots, at 1280×720 and 1920×1080
(`pipeline-<w>x<h>.png` in `web/e2e/screenshots/`).

## Tests

Vitest (quote the contract names in test titles where they apply):
- Reducer (Step 5 verbatim): "`started` → decisions → `finished`; lane counts sum to `processed`; foreign `run_id`
  ignored; `previous` kept on a new start; the event cap is 500." Also: `routedByCategory`, agreement, tokens, errors,
  latencies keep the last 50.
- "`RerunDelta` shows the sign." (positive, negative and zero)
- LiveFeed renders ≤ 100 rows when given 500 events (assert exactly 100), and a row click navigates to the Studio URL.
- StatsStrip: p50/p95 and agreement % on known inputs; the cost is hidden in mock mode and shown in live mode.
- ReviewQueue shows the exact `lane_reason` strings; Accept / Override make NO fetch call (spy on `fetch`) and update the
  visible state; the "simulated reviewer" label is visible.
- `useDecisionStream`: with a mock `EventSource`, the `decision` and `run` listeners call `onEvent` with the right
  `kind`, `seq` and `data`; `connected` follows open/error; the source is closed on unmount.
- RunControls: Start sends the chosen source and pace (`max` → `rate_per_s: null`); Stop posts to the current run id.

Planted bugs the evaluator will try; each must fail a test: drop the foreign-run_id check; remove the 500 cap; remove the
100-row slice; don't move `current` to `previous`; lose the Δ sign; make Accept call `fetch`; not close the EventSource;
remove the backend restart rule.

Playwright (titles verbatim from Step 5; new file e.g. `web/e2e/pipeline.spec.ts`; the auto network guard stays active):
1. "Start with source unit and pace max; wait for "finished"; the four lane counters sum to `total` from the start
   response." Read `total` from the actual `POST /pipeline/run` response (`page.waitForResponse`).
2. "Stop mid-run at pace 1/s → status "stopped", and processed < total."
3. "Re-run with quality threshold 95 → the RerunDelta review count increases."
4. "Clicking a review item shows its `lane_reason`." Assert it matches one of the D1 lane-reason formats
   (e.g. `score 80 < threshold 95`, `NIK gate failed: P(valid) 0.08`), not just non-empty.
6. "No console errors during a full run." Collect `console` errors and `pageerror`s for a full run.
Also: a full `all`-source run at max pace (204 events) renders EXACTLY 100 feed rows (a unit run has only 60, which would
prove nothing).

**Important: the pipeline runner is one global runner on the shared e2e server, and starting a run stops the one in
progress.** Tests that start runs (the pipeline spec AND the pipeline screenshots) must never run concurrently with each
other: keep them in one file run serially (`test.describe.configure({ mode: "serial" })`), or otherwise guarantee it, and
say how in your report. Don't disable the network guard; if `EventSource` doesn't work through it, stop and explain.

## Out of scope (D3b / D4)
The observability drawer and `parsePrometheus` (Step 4), spec 5, two-tab and kill/restart reconnect checks, presenter
mode, the `O` shortcut, Benchmarks. No change to the D2 pages beyond wiring the route.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e        # D2 specs + D3 specs 1,2,3,4,6 + 100-row check + screenshots
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)                        # nothing
make web-types && git diff --exit-code web/src/api/schema.d.ts                                 # schema unchanged
make lint && make typecheck && make test                                                       # backend 408 + new
```
Real server (paste the real output; `curl -D -` if you need headers, never `curl -I`):
```bash
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18731 &
PID=$!; sleep 2
curl -s -X POST localhost:18731/api/v1/demo/pipeline/run -H 'Content-Type: application/json' \
  -d '{"source":"unit","rate_per_s":1}'
sleep 3; curl -s -X POST localhost:18731/api/v1/demo/pipeline/<run_id>/stop
curl -s 'localhost:18731/api/v1/demo/decisions?limit=1'; sleep 3; curl -s 'localhost:18731/api/v1/demo/decisions?limit=1'
# the seq must be the same in both
kill $PID; wait $PID
```

## Report back with
Everything AGENTS.md's "Final message" asks for (before: backend 408 at 98%, web Vitest 28, Playwright 8), plus:
- the output of every Verify command, and the real-server output above
- per-file coverage of `sse.py` (and `feed.py` if touched)
- how you kept run-starting e2e tests from overlapping
- the choices you made where this prompt offered one (thresholds payload, percentile method, Δ sign characters)
- the list of screenshot files with sizes, and a short description of what the Pipeline screenshot shows
