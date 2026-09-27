Fixed all three D2a evaluator findings.

Changed:
- [scripts/dump_openapi.py](/home/budi/code/sphere_project/FHIR_JEV/scripts/dump_openapi.py)
- [web/e2e/fixtures.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/fixtures.ts)
- [web/e2e/overview.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/overview.spec.ts)
- [web/eslint.config.js](/home/budi/code/sphere_project/FHIR_JEV/web/eslint.config.js)
- All handwritten web `.ts`, `.tsx`, and config files reformatted to ≤100 columns.

Results:
- Samples are normal readable JSON again; `u002f` counts are all `0`.
- FHIR terminology URLs remain visible in samples and are data only.
- Network guard is automatic for every Playwright test, blocks non-local requests, records them, and fails in teardown with blocked URLs.
- ESLint enforces `max-len: 100` with the requested ignore settings.
- `make web-test`: 12/12 passed, 1.19s.
- `make web-e2e`: 2/2 passed, 5.8s.
- Backend: 408/408 passed, 8.82s; 98% total coverage.

Guard mutation verification, with host check replaced by `if (false)`:

```text
✓  1 … Overview loads, and the mode badge says MOCK.
✓  2 … network guard catches and records an external request

Expected to fail, but passed.

1 failed
1 passed
make: *** [Makefile:59: web-e2e] Error 1
```

The real host check was restored afterward. All requested verification commands passed, including the plain-JSON and 100-column scans.