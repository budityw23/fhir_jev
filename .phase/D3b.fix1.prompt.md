D3b fix-up round 1. Same rules as before (AGENTS.md and .phase/D3b.prompt.md; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). No new dependencies. No backend changes.

As you said, D3b isn't complete yet. The evaluator reviewed what exists:
- ✅ `parsePrometheus`, the captured `metrics.txt`, the drawer structure, `getLastRequest` / `apiText`, the "disconnected"
  indicator, the additive CSS. Keep them.
- ✅ Your finding is confirmed: `jev_fhir_decisions_total` is only incremented by the Phase 4 routes, so it has no samples
  after demo calls. Don't change the backend. The evaluator records it for Budi.
Finish EVERYTHING below; this is the main job of the round.

## 1. Small code fixes (❌)
- **Toggle:** the contract says the drawer is "toggled from the TopBar". The TopBar button currently only opens it; make
  it toggle (open ↔ closed), keeping `aria-expanded` in sync.
- **Race:** if a live decision arrives before the initial `GET /decisions?limit=50` resolves, `setDecisions(items)`
  overwrites it. Merge instead: combine the fetched items with the ones already received, de-duplicated by `seq`, newest
  first, capped at 50.
- **Readability:** reformat `MetricsTable` in `ObservabilityDrawer.tsx` to normal multi-line JSX like the other
  components (lines ≤ 100). Formatting only; don't reformat other files.
- When the Decisions metrics table has no rows, show a short note instead of an empty table (e.g. "No decision metrics
  yet: demo calls don't increment jev_fhir_decisions_total"), so the demo audience isn't shown an empty grid.

## 2. Vitest (❌): add ALL of these (the D3b prompt's list)
- "`parsePrometheus` on a captured metrics sample." (verbatim title) with specific entries from `metrics.txt` (name,
  labels incl. `endpoint="/compare/{module}"`, value), plus edge cases: escaped `\"` and `\\` and `\n`, a comma inside a
  quoted label value, `+Inf` / `-Inf` / `NaN`, a sample without labels, a trailing timestamp, `# HELP` / `# TYPE` skipped.
- Drawer:
  - the TopBar button toggles it open and closed (and `aria-expanded` follows); `Escape` and the Close button close it
  - on open it fetches `/api/v1/demo/decisions?limit=50` and renders one JSON line per decision
  - live decision events from a mocked `EventSource` are prepended; an event received before the fetch resolves is kept
    (the race above); the EventSource exists only while the drawer is open (closed on close)
  - the last request id / duration published via `subscribeLastRequest` / `api()` BEFORE opening are shown, and update
    after a later request
  - metrics are fetched on open and every 5 s (fake timers), and polling stops after close (count `fetch` calls)
  - both tables render from a metrics string; the empty-decisions note shows when there are no decision samples; the
    "Show raw" toggle shows and hides the raw text; a failed metrics fetch shows the inline error
- Pipeline: the stream indicator shows "disconnected" after an EventSource `error` and "connected" after `open`.

The evaluator will plant these bugs; each must make at least one test FAIL. Run each, confirm the failure, restore:
split labels on every comma (ignore quoting); don't unescape; don't clear the metrics interval on close; ignore live
events in the drawer; make the drawer show a stale/initial request id only; render "connecting" instead of
"disconnected"; make the TopBar button open-only.

## 3. Playwright (❌)
- Spec 5 (verbatim title): "The drawer opens and shows a request id and a parsed metrics table." Assert a non-empty
  request id AND at least one parsed row in the HTTP requests table. Also: trigger an API call (e.g. on a Studio page),
  capture its `X-Request-Id` response header with `page.waitForResponse`, open the drawer, and assert the drawer's
  request id equals that header — unless the drawer's own requests already replaced it, in which case assert it equals
  the header of the LAST API response the page received (track responses with `page.on("response")`).
- Two tabs: two pages on `/demo/pipeline`; one starts a unit run at max pace; both reach "Status: finished" with the same
  processed count.
- Kill + restart during a run, preferably as a spec with its OWN uvicorn child (port 8011, built UI at `/demo`), exactly
  as described in the D3b prompt: "disconnected" after the kill, "connected" after the restart WITHOUT a reload (e.g. set
  `window.__marker` before and assert it survives), then a new run's events arrive (processed > 0). Kill the child in
  `finally`/`afterAll`. If it can't be made reliable, write the exact manual procedure in your report and say why.
- Add drawer screenshots (`drawer-<w>x<h>.png`, Pipeline page with the drawer open after a finished run).

## 4. Final D3 regression (❌): run it and paste the output
Everything in the D3b prompt's "Final D3 regression" block, from a clean `rm -rf web/node_modules`, with `make web-e2e`
run twice, plus the real-server stop/seq curls.

## Report back with
Changed files; Vitest 38 → after; Playwright 14 → after; both `make web-e2e` summaries; for each of the 7 planted bugs,
the Vitest summary line showing the failure; the kill/restart output (or the procedure); the screenshot files with sizes;
anything you couldn't do, stated plainly at the end.
