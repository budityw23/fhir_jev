Implement Phase D4a — Benchmarks page, from docs/Jev × FHIR — Demo Technical Implementation Plan.md.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2–D3 built the shell, Studio, Playground, Pipeline and
the observability drawer; reuse their components (`ErrorCard`, `LaneChip` styling, `JsonView`), `api()`, the TanStack
Query hooks, `lib/format.ts`, and the e2e network guard in `web/e2e/fixtures.ts`. Keep the lessons:
- never obfuscate data to pass a check
- **finish the whole phase before you stop.** In D3a and D3b your first pass stopped after the code with most tests
  missing. Don't end your turn until every item under "Scope" and "Tests" exists and the Verify block passes; if you truly
  can't, list exactly what is missing at the end
- every test must fail when the behaviour it names is removed; **run the planted bugs listed below yourself** and report
  the failing summary line for each (you skipped this in D3a/D3b)
- avoid vacuous tests: no `?? ""` inside `toContain`, no identical mock values that hide staleness, fake timers enabled
  before the thing they drive is created
- lines ≤ 100 chars; ESLint `max-len` keeps covering JSX; don't reformat files you don't change
- the evaluator VIEWS the screenshots: readable, spaced, labelled, no horizontal scroll

Read before you start:
- the plan: "## Phase D4" → "How D4 Is Organised" (incl. "Decisions and clarifications"), "D4 Contract" Steps 1, 2 and 7,
  and "#### Phase D4a" (scope, tests, checklist)
- docs/Jev × FHIR — Demo Plan Requirement.md UI-B-1…7b

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies (Recharts is
installed). **No backend changes.** Never run `make bench-live*` or any live Jev call.

## Facts about the data (verified by the evaluator)
- `GET /api/v1/demo/benchmarks` → `BenchmarkSummary[]` (`name`, `generated_at`, `mode`, `dataset`, `jev_model`), newest
  first. `GET /api/v1/demo/benchmarks/{name}` → the raw report JSON (untyped in OpenAPI). `mode` is `"mock_jev"` or
  `"live_jev"`.
- Report shape (see `benchmarks/bench_runner.py` and e.g. `benchmarks/results/bench_20260927T120759Z.json`, the mock
  **full** report): top level `generated_at`, `mode`, `jev_model`, `dataset`, `quality_labels_banded`,
  `token_and_cost {tokens_used, estimated_cost_usd, pricing_note}`, `modules`. `modules` has `quality_scorer`,
  `bundle_router`, `notifiable_detector`, each with `fixture_count`, `jev_accuracy`, `rule_accuracy`,
  `latency {mean_ms, p50_ms, p95_ms}`, `confidence_calibration [{bucket, count, mean_confidence, observed_accuracy}]`,
  `rows [...]`, `breakdown {source, difficulty}` and `unapproved_labels` (per module, NOT top level). The notifiable
  module also has `jev_precision_recall_f1` / `rule_precision_recall_f1`; quality also has `jev_score_in_band`.
- Rows use the catalog fixture id (`fixture`, e.g. `tests/fixtures/bundles/lab_bundle.json`) plus `jev_correct` /
  `rule_correct` and module-specific fields (`expected_action` / `jev_action` / `rule_action`; `expected_category` /
  `jev_category` / `rule_category`; `expected_notifiable` / `jev_notifiable` / `rule_notifiable`).
- Old pre-D0 reports (`bench_20260924T0834…`, `…0837…`, `…0850…`) have no `dataset`, no `quality_labels_banded` and no
  `breakdown`. The unit mock reports (`…151507Z`, `…154552Z`) have router `jev_accuracy` **0.733**.
- There is NO live report. Don't create one under `benchmarks/results/`. Live-only parts are tested with a synthetic live
  report in a test fixture (Vitest) and, for e2e/curl, in a temporary copy of the results directory served via the
  `DEMO_RESULTS_DIR` setting (check `src/jev_fhir/config.py` for the exact env var name).

## Scope (D4a only)

### Types
The report isn't in OpenAPI: add hand-written report types (e.g. `web/src/api/benchmarks.ts` or next to `RunEvent` in
`types.ts`), mirroring the shape above, with a comment. Handle missing fields in old reports (optional types).

### Step 1: `web/src/lib/prdTargets.ts`, exactly as in the contract.

### Step 2: the Benchmarks page at `/benchmarks` (replace the placeholder), components in `web/src/components/benchmarks/`
- **ReportSelector:** lists `/benchmarks` newest first; each option shows name, a prominent mock/live badge, dataset and
  model. The selected report is in the URL (`?report=<name>`); the default is the newest.
- **AccuracyTable:** rows quality / router / notifiable × columns Jev, Rules, PRD target. The chip reads PASS (green) or
  FAIL (red) with text, never hidden. Quality and router compare `jev_accuracy` with `min`; notifiable uses Jev recall ≥
  `recallMin` AND precision ≥ `precisionMin` from `jev_precision_recall_f1`.
- **BreakdownTable:** per module, by source and by difficulty (count, Jev, Rules). Rendered only when
  `dataset === "full"`.
- **LatencyPanel:** mean/p50/p95 per module with the PRD lines (p50 ≤ 30 ms, p95 ≤ 100 ms) and a pass/fail mark.
- **CalibrationChart:** Recharts; per bucket mean confidence vs observed accuracy, with a y = x reference line;
  `isAnimationActive={false}`.
- **DisagreementList:** rows where `jev_correct !== rule_correct` or both are false, per module, showing fixture, expected,
  Jev, Rules. Clicking a row navigates to `/studio/{quality|router|notifiable}?fixture=<fixture id>` (map the report's
  module names to the Studio's).
- **NotifiablePRF:** Jev vs Rules precision / recall / F1.
- **MockDisclaimer:** when `mode === "mock_jev"`, exactly: *Mock decisions mirror rule logic; this report validates the
  harness, not Jev.*
- **LiveMeta:** when `mode === "live_jev"`: model, run timestamp, total tokens and estimated cost.
- **LabelGuard:** when `quality_labels_banded !== true` (incl. missing), the quality accuracy cell and chip are replaced by
  exactly *labels not suitable for live scoring*.
- **LiveVsMock:** when the latest live and latest mock reports for the same dataset both exist, side-by-side accuracy
  columns (mock vs live) per module.
- **Unapproved banner:** when any module's `unapproved_labels > 0`, a warning banner with the per-module counts.
- Empty state: no reports → "no report yet". API errors → `ErrorCard`.

### Screenshots
Add the Benchmarks page (newest report = the mock full report) to the screenshots spec at 1280×720 and 1920×1080
(`benchmarks-<w>x<h>.png`). `workers: 1` stays.

## Tests
Vitest (titles from Step 7 verbatim where they apply):
- "`LabelGuard` hides quality accuracy for unbanded reports." (both `false` and missing)
- "The PRD chip shows FAIL for 0.733 routing." Also PASS at 0.90 exactly, and the notifiable rule (recall and precision).
- BreakdownTable only for `dataset === "full"`; MockDisclaimer text exact and only for `mock_jev`; LiveMeta only for
  `live_jev` with model, tokens and cost; LiveVsMock only when both a live and a mock report exist for the same dataset;
  the banner only when some module has `unapproved_labels > 0`; DisagreementList includes exactly the disagreement /
  both-wrong rows and its click navigates to the mapped Studio URL; LatencyPanel pass/fail against the PRD lines.
- Use a synthetic live report fixture under `web/src/test/fixtures/` (derived from the mock full report with
  `mode: "live_jev"`, a model id and non-zero tokens/cost), clearly named as synthetic.

Planted bugs (run each, confirm a test fails, restore exactly, report the failing summary line):
PRD chip compares with `>` 0.85 instead of `min`; hide the chip on FAIL; show BreakdownTable for unit reports; change one
word of the disclaimer; LabelGuard checks `=== false` (misses missing); DisagreementList drops the both-wrong rows; map
`bundle_router` to `/studio/quality`; show the banner when all counts are 0.

Playwright (titles verbatim from Step 7):
1. "The benchmarks page shows the latest report; the mock report shows the disclaimer and router FAIL." (latest = the mock
   full report; also select a unit report and see router 0.733 with FAIL)
2. "A disagreement row click opens Studio with that fixture." (assert the Studio URL and that the picker has that
   fixture selected)
Plus: a pre-D0 report shows "labels not suitable for live scoring"; no horizontal scroll at 1280×720
(`document.documentElement.scrollWidth <= innerWidth`); no console errors.

## Out of scope
Scenes and presenter controls (D4b); global polish, contrast, runbook (D4c); any backend change; UI-B-8.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e        # run make web-e2e twice
make web-types && git diff --exit-code web/src/api/schema.d.ts
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)                        # nothing
make lint && make typecheck && make test                                                       # backend 412
git status --porcelain benchmarks/                                                             # nothing new
```
Real server (paste real output): `curl -s localhost:<port>/api/v1/demo/benchmarks | head -c 600` and
`curl -s localhost:<port>/api/v1/demo/benchmarks/bench_20260927T120759Z | head -c 300`; stop it by its PID.

## Report back with
Everything AGENTS.md's "Final message" asks for (before: backend 412, Vitest 47, Playwright 16), plus the output of every
Verify command, the failing summary line for each of the 8 planted bugs, the screenshot files with sizes and a short
description of the Benchmarks screenshot, and anything you couldn't do, stated plainly at the end.
