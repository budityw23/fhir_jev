Changed only [benchmarks.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/benchmarks.spec.ts) and [screenshots.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/screenshots.spec.ts). All existing assertions remain.

The benchmark test now checks the initial selection against the first option’s value, then selects `bench_20260927T120759Z` for mock assertions. The screenshot capture selects that report too.

Ordering confirmed from code: `list_reports()` sorts timestamped filenames descending; `useBenchmarks()` preserves the response order; `ReportSelector` renders options in that order; the page defaults to `summaries.data[0]`.

Verification output:

```text
make lint: All checks passed! 69 files already formatted
make typecheck: Success: no issues found in 62 source files
make test: 456 passed, 805 warnings in 11.60s
TOTAL coverage: 98%

npm run lint: passed
npm run typecheck: passed
npm run test: 60 passed (60), Duration 4.23s

With live report: 29 passed (48.3s)
Committed reports only: 29 passed (44.5s)
```

Test counts remain backend 456 → 456, unit 60 → 60, e2e 29 → 29. No application source changed, so per-file source coverage is inapplicable.

Copied the 12 git-tracked report files to `web/test-results/committed-reports/`. Used `DEMO_RESULTS_DIR`, confirmed from `config.py`, and `--output=test-results/committed-run` to preserve the copies during Playwright cleanup. Actual curl output during each run:

```text
# Default directory
reports: bench_20261031T150439Z, bench_20260927T120759Z, bench_20260924T154552Z, bench_20260924T151507Z, bench_20260924T085042Z, bench_20260924T083720Z, bench_20260924T083443Z
live report listed: True

# Overridden directory
reports: bench_20260927T120759Z, bench_20260924T154552Z, bench_20260924T151507Z, bench_20260924T085042Z, bench_20260924T083720Z, bench_20260924T083443Z
live report listed: False
```

Both planted checks failed as required:

```text
# Live report selected instead of mock
✘  1 e2e/benchmarks.spec.ts:7:1 › The benchmarks page shows the latest report; the mock report shows the disclaimer and router FAIL. (5.3s)
Error: expect(locator).toBeVisible() failed
Locator: getByText('Mock decisions mirror rule logic; this report validates the harness, not Jev.')
Error: element(s) not found
1 failed

# Wrong expected selection
✘  1 e2e/benchmarks.spec.ts:7:1 › The benchmarks page shows the latest report; the mock report shows the disclaimer and router FAIL. (5.3s)
Error: expect(locator).toHaveValue(expected) failed
Expected: "bench_wrong_report"
Received: "bench_20261031T150439Z"
1 failed
```

Before planting and after each restoration, the benchmark spec and backup matched:

```text
86cca15f78a2f0a9055e8131e3b6c5082f713d4f
```

The screenshot spec and backup also matched:

```text
b190d59e64c81b2b41dcbf5547d245fe79e1eb05
```

Verification copies and planted-check artifacts were removed. No tracked screenshots changed; none exist under `web/e2e/screenshots/`. No server remains running: the process check was empty, and curl returned:

```text
curl: (7) Failed to connect to 127.0.0.1 port 8010 after 0 ms: Couldn't connect to server
```

Final `git status --porcelain`:

```text
 M src/jev_fhir/modules/notifiable_detector.py
 M src/jev_fhir/serializer/condition.py
 M tests/test_decision_modules.py
 M tests/test_serializer.py
 M web/e2e/benchmarks.spec.ts
 M web/e2e/screenshots.spec.ts
 M web/src/components/benchmarks/BenchmarkParts.tsx
 M web/src/index.css
 M web/src/pages/Benchmarks.tsx
 M web/src/pages/Overview.tsx
 M web/src/pages/Pipeline.tsx
 M web/src/pages/Playground.tsx
 M web/src/pages/Studio.tsx
 M web/src/test/fixtures/compare_notifiable.json
?? .phase/codetext.prompt.md
?? .phase/codetext.result.md
?? .phase/e2efix.prompt.md
?? .phase/video.prompt.md
?? .phase/video.result.md
?? benchmarks/results/bench_20261031T150439Z.json
?? benchmarks/results/bench_20261031T150439Z.md
?? "docs/Jev \303\227 FHIR \342\200\224 Article Draft.md"
?? "docs/Jev \303\227 FHIR \342\200\224 Code Text Fix Plan.md"
?? "docs/Jev \303\227 FHIR \342\200\224 LinkedIn Article Draft.md"
?? "docs/Jev \303\227 FHIR \342\200\224 LinkedIn Post Draft.md"
?? docs/demo-video/
?? web/video/
```

All entries except the two specs were present initially. No helpers or deviations added. Questions for the evaluator: none.