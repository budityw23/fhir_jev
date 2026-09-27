Implement Phase D3b — Observability drawer, reconnect, and final D3 regression, from
docs/Jev × FHIR — Demo Technical Implementation Plan.md. This is the last D3 sub-phase.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D3a (Live Pipeline, `useDecisionStream`, the reducer,
the SSE restart rule, `workers: 1` for e2e) is done; reuse it. Keep the lessons:
- never obfuscate data to pass a check
- add EVERY test listed below, and check each one fails when its behaviour is removed (the evaluator plants bugs; last
  time the first pass shipped 3 of ~20 required tests)
- lines ≤ 100 chars; ESLint `max-len` keeps covering JSX (no `ignoreStrings`); don't reformat files you don't change
- the evaluator VIEWS the screenshots: readable, spaced, labelled layout

Read before you start:
- the plan: "## Phase D3" → "How D3 Is Organised", "D3 Contract" Step 4 (drawer) and Step 5 (tests), "#### Phase D3b"
  and its **Final D3 checklist**
- docs/Jev × FHIR — Demo Plan Requirement.md UI-G-4

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies. **No backend
changes.**

## Scope (D3b only)

### 1. `parsePrometheus` (Step 4 signature exactly), e.g. in `web/src/lib/prometheus.ts`
```ts
export function parsePrometheus(text: string): Array<{ name: string; labels: Record<string, string>; value: number }>;
```
- Skip `# HELP` / `# TYPE` / blank lines. Parse `name{k="v",...} value` and `name value`. Label values may contain commas,
  `=`, spaces, `{}` (e.g. `endpoint="/compare/{module}"`) and escaped `\"`, `\\`, `\n`; unescape them. Values may be
  `1.0`, `3`, `1e-05`, `+Inf`, `NaN`. An optional trailing timestamp is ignored.
- Capture a REAL sample from a running mock server into `web/src/test/fixtures/metrics.txt` (run a unit pipeline and a
  few demo calls first, then `curl -s localhost:<port>/api/v1/metrics`). Don't hand-edit it. If
  `jev_fhir_decisions_total` has no sample lines after the demo calls, say so in the report (don't change the backend);
  the Vitest test may then add a small hand-written string for that metric, clearly separate from the captured file.

### 2. Observability drawer (Step 4, UI-G-4), e.g. `web/src/components/shell/ObservabilityDrawer.tsx`
- A slide-over toggled by a TopBar button (replace the "Observability drawer placeholder" span with a real button,
  `aria-expanded`, accessible name "Observability"). The `O` key is D4, not now. Closable (button and `Escape`).
- **Decisions:** on open, `GET /api/v1/demo/decisions?limit=50` via `api()`, then live updates from
  `useDecisionStream` (decision events prepended, keep 50), shown as JSON lines (one `JSON.stringify(event)` per line,
  newest first). The stream is opened only while the drawer is open.
- **Last request:** the last request's `X-Request-Id` and `X-Request-Duration-Ms` from `subscribeLastRequest`
  (`data-testid="last-request-id"`, `"last-request-duration"`), plus its path. Subscribe for the app's lifetime (e.g. in
  a small store/hook created at app start), so the drawer shows the last request made BEFORE it was opened; the drawer's
  own polling requests also update it (that's fine and expected).
- **Metrics:** while open, fetch `/api/v1/metrics` every 5 s (text, not JSON: use `fetch` directly or extend `api()`
  with a text variant without changing its existing behaviour); stop polling on close/unmount. Show two tables:
  `jev_fhir_decisions_total` (module, decision, count) and `jev_fhir_http_requests_total` (endpoint, method, status,
  count). A "Show raw" toggle shows the raw text. A metrics fetch failure shows an inline error, not a crash.
- The Pipeline page's stream indicator must read exactly **"disconnected"** after `onerror` and **"connected"** after
  `onopen` (today it says "connecting" on error; the final checklist item says "page shows disconnected").

### 3. Reconnect proofs
- **Two tabs:** a Playwright test with two pages (same context) on `/demo/pipeline`; one starts a unit run at max pace;
  BOTH pages reach "Status: finished" with the same processed count.
- **Kill + restart during a run:** preferred as a Playwright spec with its OWN controlled uvicorn (e.g. spawn
  `.venv/bin/python -m uvicorn jev_fhir.main:app --port 8011` with `DEMO_ENABLED=true MOCK_JEV=true` via
  `child_process`, serving the built UI at `/demo`): open `/demo/pipeline`, start a run at pace 1, wait for a few
  events, kill the server → the page shows "disconnected" → restart it on the same port → the page shows "connected"
  WITHOUT a reload (assert no `load` event / same `window` marker) → start a new run → the page receives its events
  (processed > 0 for the new run). Always kill the child server in `finally`/`afterAll`. The network guard stays on.
  If that is not reliable in the sandbox, write it as an exact manual procedure in your report instead and say why;
  the evaluator will run it.

## Tests
- Vitest (verbatim from Step 5): "`parsePrometheus` on a captured metrics sample." Assert specific parsed entries
  (name, labels incl. `endpoint="/compare/{module}"`, value) from the captured file, plus edge cases: escaped quotes,
  `+Inf`/`NaN`, a sample without labels, `# HELP/# TYPE` skipped.
- Vitest, drawer: opens/closes via the button (and `Escape`); fetches `/decisions?limit=50` on open and renders JSON
  lines; shows the last request id/duration published through `subscribeLastRequest` before opening; polls metrics
  every 5 s with fake timers and stops after close (count `fetch` calls); renders both tables from a metrics string; the
  raw toggle shows the raw text.
- Vitest: the Pipeline stream indicator shows "disconnected" after an EventSource error and "connected" after open.
- Playwright spec 5 (verbatim): "The drawer opens and shows a request id and a parsed metrics table." Also assert the
  shown `X-Request-Id` equals the `X-Request-Id` header of the last API response (capture with `page.waitForResponse`
  on a request you trigger, e.g. while on the Studio page) — this is the final checklist item "Drawer shows
  X-Request-Id matching the last response header".
- Playwright: the two-tab test and (preferably) the kill/restart test above.

The evaluator will plant bugs such as: `parsePrometheus` not unescaping / splitting labels on commas inside quotes;
metrics polling not stopped on close; the drawer ignoring live events; showing a stale request id; the indicator never
showing "disconnected". Each must fail a test.

## Out of scope
Presenter mode, the `O` shortcut, Benchmarks (D4). No backend change. No change to D2/D3a behaviour beyond the TopBar
button and the stream indicator wording.

## Final D3 regression (do this last and paste the evidence)
Run the plan's **Final D3 checklist** from a clean `rm -rf web/node_modules`:
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
rm -rf web/node_modules && make web-install
make web-test && make web-types && git diff --exit-code web/src/api/schema.d.ts
make web-build && find web/dist -type f ! -name '*.map' -size +1M               # nothing
make web-e2e                                                                    # all D2 + D3 specs; run it twice
grep -rn "http://\|https://" web/src --exclude=schema.d.ts | grep -v "src/test/fixtures/"   # nothing
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)          # nothing
make lint && make typecheck && make test                                        # backend 411
```
Real server (paste the real output): start a paced unit run, stop it, `curl -s '<base>/decisions?limit=1'` twice 3 s
apart (same seq); stop the server by its PID.
Add a drawer-open Pipeline screenshot (`drawer-<w>x<h>.png`, both sizes) to the screenshots.

## Report back with
Everything AGENTS.md's "Final message" asks for (before: backend 411, web Vitest 38, Playwright 14), plus:
- the output of every Final D3 checklist command (both e2e runs)
- whether `jev_fhir_decisions_total` had samples in the captured metrics
- how the kill/restart check was done (spec or manual procedure), with its output
- the screenshot files with sizes and a short description of the drawer screenshot
- anything you could not do as written, stated plainly at the end
