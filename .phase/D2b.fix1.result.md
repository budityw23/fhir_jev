Implemented D2b fix-up round 1.

Changed:
- `.gitignore` — ignores `web/*.tsbuildinfo`
- `web/eslint.config.js` — JSX line-length rule now applies to strings/templates
- `web/src/index.css` — lane-chip styles
- `web/src/components/studio/LaneChip.tsx` — new lane icon/name/reason display
- `DecisionCard.tsx`, `VerdictStrip.tsx`, `ThresholdSliders.tsx`, `NoulMeter.tsx`, and other Studio/Overview components — formatted to ≤100 chars; lane rendering and verdict expectation added
- `web/src/pages/Studio.tsx` — exported/tested exact question selection helper, formatting only otherwise
- `web/src/test/studio.test.tsx` — 10 Studio tests covering lane/reason, verdict expectations, Dinkes, live/mock distribution, sliders, picker, questions, and debounce
- `web/e2e/studio.spec.ts` — verbatim Step 11 titles; quality lane-reason assertion

Results:
- Vitest: 15 → 22 tests, 6 files passed, 2.15s.
- Playwright: 6 passed, 9.8s.
- Build passed; no non-map web artifact exceeds 1 MB.
- Hand-written web TS/TSX/JS line-length audit: no output.
- Backend unchanged: `make lint`, `make typecheck`, and 408 tests passed in 9.37s; 98% coverage.

Mutation checks performed and restored:

| Mutation | Failing Vitest summary |
|---|---|
| Remove Dinkes `lane === "flagged"` guard | `Test Files 1 failed \| 5 passed (6)` / `Tests 1 failed \| 21 passed (22)` |
| Always render LevelDistribution | `Test Files 1 failed \| 5 passed (6)` / `Tests 1 failed \| 21 passed (22)` |
| Render router slider for all modules | `Test Files 1 failed \| 5 passed (6)` / target slider test failed (an additional debounce locator failure followed because the failed render remained mounted) |
| Change `draft` marker | `Test Files 1 failed \| 5 passed (6)` / `Tests 1 failed \| 21 passed (22)` |
| Use notifiable statement for router | `Test Files 1 failed \| 5 passed (6)` / `Tests 1 failed \| 21 passed (22)` |
| Change Studio debounce to 0 ms | `Test Files 1 failed \| 5 passed (6)` / `Tests 1 failed \| 21 passed (22)` |

No backend changes or open evaluator questions.