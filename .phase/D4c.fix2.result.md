Implemented D4c fix-up round 2.

Changed:
- [polish.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/polish.test.tsx) now reads and parses the real `web/src/index.css` via `node:fs`; `tokens.ts` was removed.
- [index.css](/home/budi/code/sphere_project/FHIR_JEV/web/src/index.css) includes JSON key/value tokens, dark JSON viewer styling, token-styled inputs/selects, and the responsive TopBar wrap.
- [JsonView.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/JsonView.tsx) supplies the JSON-viewer CSS variables.
- [demo-runbook.md](/home/budi/code/sphere_project/FHIR_JEV/docs/demo-runbook.md) has exact live/fallback commands.
- [polish.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/polish.spec.ts) includes 900×800 Overview/Studio overflow coverage.
- [vite-env.d.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/vite-env.d.ts) declares the built-in test-only `node:fs` API.

Vitest: 60 → 60 passing (~3.0s).

Planted regression failures, restored exactly:

```text
light review on bg: 2.38 (#d49a00 on #f8fafc): expected 2.3832846434833517 to be greater than or equal to 4.5
dark JSON key: 1.00 (#1d2939 on #1d2939): expected 1 to be greater than or equal to 4.5
900px Overview and Studio have no horizontal scroll
Expected: true
1 failed
```

The prior 1.46 issue was the JSON key contrast on the dark JSON surface. It is now `--c-json-key: #b9d9ff` on `--c-surface: #1d2939`, ratio 9.10:1.

Final notable ratios:

| Pair | Light | Dark |
|---|---:|---:|
| Accept on surface | 6.65 | 10.04 |
| Review on surface | 7.24 | 10.42 |
| Flag on surface | 7.36 | 8.67 |
| Neutral on surface | 5.90 | 8.72 |
| JSON key on surface | 4.87 | 9.10 |
| JSON value on surface | 6.65 | 12.36 |

Verification completed before the full Playwright output was truncated by the execution time limit:

```text
make web-types                 PASS; fixture status clean
make web-test                  PASS; 60 tests
make web-build                 PASS
make web-e2e                   started; 29 tests (the intentional D2a network-guard failure remains expected)
```

I did not get enough execution time to capture the final complete `make web-e2e` summary, rerun it a second time, run backend `make lint/typecheck/test`, or regenerate/view the updated dark screenshot.