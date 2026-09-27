D4a fix-up round 1. Same rules as before (AGENTS.md and .phase/D4a.prompt.md; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). No backend changes, no new dependencies. Finish every item
before you stop; if you can't, list exactly what is missing.

The evaluator reproduced D4a: lint, typecheck, Vitest 51, build, backend 412 are green; the page logic mostly matches the
contract. Problems:

## 1. e2e spec 1 fails (❌)
`make web-e2e`: 1 failed / 17 passed (the ✘ on "network guard catches…" is D2a's intentional expected failure; ignore
it). Spec 1 times out in `selectOption("bench_20260924T151507Z.json")`: the option values are report names WITHOUT
`.json`. Fix the test (select `bench_20260924T151507Z`), then assert router `73%` and its FAIL chip in the Router row
(scope assertions to the row, not the whole page).

## 2. Weak or missing tests (❌)
- The evaluator planted 8 bugs; 2 left all 51 tests green. Add tests so each fails:
  - `["bundle_router", "Router", "router"]` → `"quality"` (Studio link for a router disagreement goes to the wrong
    page): assert the exact href of a router row and a notifiable row.
  - the unapproved banner filter `count > 0` → `() => true`: assert NO banner when every module's count is 0.
- Spec 2 only checks that some radio is checked. Assert the checked radio is the clicked row's fixture (e.g. read the
  fixture id from the link, open Studio, and check the picker item for that fixture is checked / the Raw FHIR shows its id).
- Add the synthetic live report fixture the D4a prompt asked for (`web/src/test/fixtures/benchmark-live.synthetic.json`,
  derived from the mock full report with `mode: "live_jev"`, a model id, non-zero `tokens_used` and
  `estimated_cost_usd`) and use it in the LiveMeta / LiveVsMock tests (model, tokens and cost values asserted).
- Playwright additions from the D4a prompt that are missing: selecting a pre-D0 report (`bench_20260924T083443Z`) shows
  "labels not suitable for live scoring"; `document.documentElement.scrollWidth <= innerWidth` on the Benchmarks page
  at 1280×720; no console errors or page errors while loading and switching reports.
- `benchmarks.spec.ts` uses `// eslint-disable-next-line max-len` for the long title. Don't disable the rule; build the
  verbatim title from joined parts as `pipeline.spec.ts` does.

## 3. Contract / layout issues from the screenshot (❌; the evaluator views `benchmarks-*.png` again)
- **CalibrationChart is wrong:** it concatenates all modules' buckets on one categorical x-axis
  (`0.5-0.8, 0.8-1.0, 0.5-0.8, 0.8-1.0, 0.0-0.5, 0.8-1.0`), has no legend or module labels, and the y = x reference line
  doesn't render. The contract: "per bucket: mean confidence vs observed accuracy, with the y = x reference line". Make it
  readable per module, e.g. a Recharts `ScatterChart` (or `LineChart` with numeric axes) with x = mean confidence and
  y = observed accuracy, both numeric 0–1, one series per module with a legend, point labels/tooltips showing the bucket
  and count, and a visible y = x `ReferenceLine` from (0,0) to (1,1). Keep `isAnimationActive={false}`.
- **LabelGuard** is inline in AccuracyTable; the contract names it as a component. Extract a small `LabelGuard`
  component (same behaviour) and use it for the quality accuracy cells.
- **LatencyPanel:** show a table (module, mean, p50, p95, PASS/FAIL) with values rounded to 1 decimal ("33.3 ms"),
  with the PRD lines in the caption, instead of run-on text.
- **BreakdownTable:** six stacked full-width tables make the page very long. Lay it out compactly, e.g. one card per
  module in a responsive grid, with source and difficulty tables side by side (or one table with grouped rows).
No horizontal scroll at 1280×720.

## Planted bugs to re-run yourself (report each failing summary line)
The 8 from the D4a prompt (`> 0.85` instead of `min`; hide the FAIL chip; BreakdownTable for unit; one disclaimer word;
LabelGuard `=== false`; drop both-wrong rows; router → `/studio/quality`; banner with all counts 0).

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e      # all pass (only the intentional guard ✘); run it twice
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len                                     # nothing
make lint && make typecheck && make test                                                     # backend 412
git status --porcelain benchmarks/                                                           # nothing new
```

## Report back with
Changed files; Vitest 51 → after; both `make web-e2e` summaries; the 8 planted-bug failing lines; a short description of
the regenerated Benchmarks screenshot (calibration chart, latency table, breakdown layout); anything not done, plainly.
