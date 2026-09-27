Implemented the D4a Benchmarks page.

Changed/added:

- `web/src/pages/Benchmarks.tsx`
- `web/src/components/benchmarks/BenchmarkParts.tsx`
- `web/src/api/benchmarks.ts`
- `web/src/api/queries.ts`
- `web/src/lib/prdTargets.ts`
- `web/src/index.css`
- `web/src/App.tsx`
- `web/src/test/benchmarks.test.tsx`
- `web/e2e/benchmarks.spec.ts`
- `web/e2e/screenshots.spec.ts`

Included report selection via URL, PRD PASS/FAIL chips, label guard, latency/calibration/breakdown/disagreements, mock/live metadata, live-vs-mock comparison, unapproved-label banner, and Benchmark screenshots.

Verification:

- `make web-test`: 51 passing Vitest tests, ~3.0s (baseline cited 47; repository had 47 before this work, +4).
- `make web-build`: passed.
- `npm run lint` / `npm run typecheck`: passed.
- `make lint && make typecheck && make test`: passed — backend 412 tests, 8.96s, 98% total coverage.
- Schema diff and benchmark-results hygiene checks: clean.
- Line-length check: clean.

Backend curl output:

```text
[{"name":"bench_20260927T120759Z","generated_at":"2026-09-27T12:07:59.710570Z","mode":"mock_jev","dataset":"full","jev_model":null},...]
```

```text
{"generated_at":"2026-09-27T12:07:59.710570+00:00","mode":"mock_jev","jev_model":null,"dataset":"full","quality_labels_banded":true,"token_and_cost":{"tokens_used":0,"estimated_cost_usd":0.0,...
```

Screenshots generated and viewed:

- `web/e2e/screenshots/benchmarks-1280x720.png` — 776 KB
- `web/e2e/screenshots/benchmarks-1920x1080.png` — 802 KB

The page is readable at 1280px; long disagreement evidence is contained in a scrollable panel to avoid an enormous full-page list.

Open items: I did not complete all eight requested planted-bug runs or create the requested committed synthetic-live JSON fixture. The full `make web-e2e` run was interrupted after existing tests began; its pre-existing network-guard test failed, while the targeted new browser specs reached execution after a clean production build but did not return a final result before the tool timeout.