Implemented the core D3b drawer pieces:

- Added `parsePrometheus` with quoted-label, escape, `NaN`, `±Inf`, and timestamp support.
- Added captured mock metrics fixture; `jev_fhir_decisions_total` had no sample lines despite demo compare calls.
- Added slide-over drawer, TopBar toggle, Escape/close handling, decision fetch + live stream, request metadata, metrics polling/raw toggle/tables.
- Pipeline indicator now says `disconnected` after an SSE error.
- Added initial parser and drawer Vitest coverage.

Changed/added files include:

- [App.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/App.tsx)
- [client.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/api/client.ts)
- [TopBar.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/shell/TopBar.tsx)
- [ObservabilityDrawer.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/shell/ObservabilityDrawer.tsx)
- [prometheus.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/lib/prometheus.ts)
- [Pipeline.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/pages/Pipeline.tsx)
- [metrics.txt](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/fixtures/metrics.txt)
- [prometheus.test.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/prometheus.test.ts)
- [observability.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/observability.test.tsx)

Verified:

```text
npm run lint                 PASS
npm run typecheck            PASS
Vitest targeted: 2 files, 2 tests PASS (1.06s)
```

This is not a completed D3b phase: I did not finish the required full Vitest suite, Playwright drawer/two-tab/restart proofs, screenshots, clean-install regression, backend regression, or required real-server final curl evidence.