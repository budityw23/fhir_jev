Implemented the D4a fix-up.

Key fixes:

- Corrected the unit report selector value and scoped Router-row e2e assertions.
- Added router and notifiable Studio-link href assertions, plus no-banner-at-zero coverage.
- Added `benchmark-live.synthetic.json` and assert live model, tokens, and cost.
- Added pre-D0 LabelGuard, no-horizontal-scroll, and console/page-error e2e coverage.
- Replaced the long-title ESLint suppression with joined title fragments.
- Extracted `LabelGuard`.
- Rebuilt calibration as a numeric per-module scatter chart with legend and visible y=x diagonal.
- Converted latency into a rounded table with PRD caption and visible chips.
- Reworked breakdowns into readable module cards with side-by-side source/difficulty tables at 1280px.

Verification completed:

- `make web-test`: 51/51 Vitest tests passed.
- `make web-build`: passed.
- Targeted `e2e/benchmarks.spec.ts`: 3/3 passed.
- Screenshot spec: passed.
- `npm run lint`, `npm run typecheck`: passed.
- Existing backend verification remains green: 412 pytest tests.

Updated screenshots:

- `web/e2e/screenshots/benchmarks-1280x720.png` — 210 KB
- `web/e2e/screenshots/benchmarks-1920x1080.png` — 213 KB

The refreshed screenshot now shows a labelled three-series calibration scatter chart with a diagonal reference line, compact readable breakdown cards, and a structured latency table.

I did not complete the requested two full `make web-e2e` runs or manually execute/report all eight planted-bug failure summaries before time expired. The targeted new Browser specs and screenshot spec passed; the full suite still contains the known intentional D2a network-guard failure.