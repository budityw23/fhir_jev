D3a fix-up round 1. Same rules as before (AGENTS.md and .phase/D3a.prompt.md; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). No new dependencies. No further backend change.

The evaluator reviewed your D3a work:
- ✅ the backend restart rule, `last_seq`, and its 3 tests; `useDecisionStream`; the reducer; the page wiring. Keep them.
- ⚠️ `web/src/index.css` was reformatted (Prettier style) on top of the new pipeline rules. The evaluator checked that
  every D2 rule is unchanged apart from whitespace and leading zeros, so leave it; **don't reformat any other file**.
- ❌ As you said yourself, most of the required tests are missing. That is the main job of this round.
- ❌ The Pipeline screenshot (`web/e2e/screenshots/pipeline-1280x720.png`, which the evaluator viewed) shows layout
  defects.

## 1. Missing Vitest tests (❌): add ALL of these from the D3a prompt
Put them in `web/src/test/` (e.g. `pipeline.components.test.tsx`, `sse.test.ts`); keep `pipeline.reducer.test.ts`.
- Reducer: add a test whose title quotes Step 5 verbatim ("`started` → decisions → `finished`; lane counts sum to
  `processed`; foreign `run_id` ignored; `previous` kept on a new start; the event cap is 500."), or confirm that the
  existing tests cover every clause and name them. Also cover `routedByCategory`, agreement (`null` not judged), tokens,
  errors, and latencies keeping the last 50 (feed 60, expect 50, the oldest 10 dropped).
- "`RerunDelta` shows the sign.": positive (`+n`), negative (`−n`) and zero (`±0`); nothing is rendered without
  `previous`.
- LiveFeed: given 500 events it renders EXACTLY 100 rows; a row click navigates to `/studio/{module}?fixture={id}`
  (use a `MemoryRouter` and assert the location or the rendered route).
- StatsStrip: p50/p95 on a known list (nearest-rank), agreement % on known counts ("—" when judged is 0), throughput from
  timestamps (e.g. 10 events within 5 s of the newest plus 5 older → 2.0/s); the cost is hidden when `live` is false and
  shown, with the value, when true.
- ReviewQueue: clicking an item shows its exact `lane_reason`; Accept / Override update the visible state and make NO
  `fetch` call (spy on `globalThis.fetch`); the "simulated reviewer" label is visible.
- `useDecisionStream`: install a mock `EventSource` class on `globalThis`; assert the URL, and that dispatching a
  `decision` and a `run` MessageEvent (with `lastEventId`) calls `onEvent` with the right `kind`, numeric `seq` and parsed
  `data`; `connected` is true after `onopen` and false after `onerror`; `close()` is called on unmount.
- RunControls: Start posts `source` and `rate_per_s` (`max` → `null`, `1` → `1`) with all three modules; Stop posts to
  `/api/v1/demo/pipeline/{current.runId}/stop` and is disabled when nothing is running; each module's `ThresholdSliders`
  is rendered.

The evaluator will plant these bugs; each must make at least one test FAIL. Run each yourself, confirm the failure, and
restore the file exactly:
drop the foreign-run_id check; remove the 500 cap; remove the 100-row slice; don't move `current` to `previous`; lose
the Δ sign; make Accept call `fetch`; don't close the EventSource on unmount; map `max` to `4`.

## 2. Missing Playwright spec (❌): `web/e2e/pipeline.spec.ts`
Use the shared `test`/`expect` from `./fixtures` (the network guard stays on). Titles verbatim from Step 5:
1. "Start with source unit and pace max; wait for "finished"; the four lane counters sum to `total` from the start
   response." Read `total` from the real `POST /pipeline/run` response (`page.waitForResponse`), and also check
   `processed/total` in the StatsStrip.
2. "Stop mid-run at pace 1/s → status "stopped", and processed < total."
3. "Re-run with quality threshold 95 → the RerunDelta review count increases." Parse `{prev}` and `{curr}` from the
   RerunDelta text and assert curr > prev.
4. "Clicking a review item shows its `lane_reason`." Assert it matches a D1 lane-reason format
   (e.g. `/^score \d+ < threshold \d+$|^NIK gate failed: P\(valid\) \d\.\d\d$|^model chose unknown$/` or similar),
   not just non-empty.
6. "No console errors during a full run." Collect `console` messages of type `error` and `pageerror`s from page load to
   "finished"; expect none.
Plus: a full `all`-source run at max pace renders EXACTLY 100 `live-feed` body rows once finished.

**No overlapping runs** (one global runner on the shared e2e server; starting a run stops the one in progress):
- run the pipeline spec serially (`test.describe.configure({ mode: "serial" })`)
- AND make sure the Pipeline screenshots never run at the same time as the pipeline spec: either move the Pipeline
  screenshot capture into `pipeline.spec.ts` (as the last serial test, writing the same `pipeline-<w>x<h>.png` files),
  or set `workers: 1` in `playwright.config.ts`. Say which in your report.

## 3. Layout defects visible in the screenshot (❌; the evaluator will view the regenerated screenshots)
- RunControls: the Start / Stop / Reset buttons and the status render as run-together text ("Start Stop Reset
  finished"). Make them real, spaced buttons (Start as the primary action, Stop disabled-looking when disabled), and show
  the status as a labelled pill ("Status: finished").
- The three threshold groups are all headed "Thresholds". Label each group with its module ("Quality", "Router",
  "Notifiable") without changing `ThresholdSliders`' props (wrap each in a labelled fieldset or heading).
- ReviewQueue: "…· qualityAcceptOverride" runs together. Separate the item text from spaced Accept / Override buttons,
  and show "simulated reviewer" as a visible caption/badge. Keep the queue in a scrollable box (e.g. max height ~24rem)
  so 20+ items don't make the page several screens long.
- LaneBoard column headers are plain text ("auto_accepted 18"): show each lane with its icon + colour + name (the same
  icons as `LaneChip`: ✓ ✓ ⚑ ⚠) and the counter as a prominent number.
- ConfidenceHistogram x-axis labels overlap ("0.8-0.90.9-1"): use short labels (e.g. `0.0`, `0.1`, … `0.9`) or an
  interval that avoids overlap.
No behaviour change; the D2 screenshots must look as before.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e        # D2 specs + D3 specs 1,2,3,4,6 + 100-row check + screenshots
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)                        # nothing
make lint && make typecheck && make test                                                       # backend 411
```
Run the full `make web-e2e` at least twice in a row and report both summaries (it must be stable).

## Report back with
Changed files; Vitest 31 → after; Playwright 8 → after; both `make web-e2e` summaries; for each of the 8 planted bugs in
item 1, the Vitest summary line showing the failure; how you prevented overlapping runs; a short description of the
regenerated pipeline screenshot. If anything can't be done as written, say so plainly at the end.
