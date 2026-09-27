Completed the main D3b fix-up implementation and regression run.

Changed/added:

- [App.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/App.tsx)
- [client.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/api/client.ts)
- [TopBar.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/shell/TopBar.tsx)
- [ObservabilityDrawer.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/shell/ObservabilityDrawer.tsx)
- [prometheus.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/lib/prometheus.ts)
- [Pipeline.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/pages/Pipeline.tsx)
- [prometheus.test.ts](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/prometheus.test.ts)
- [observability.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/observability.test.tsx)
- [pipeline.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/pipeline.spec.ts)
- [screenshots.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/screenshots.spec.ts)

Implemented:

- TopBar now toggles drawer state and synchronizes `aria-expanded`.
- Live/fetched decisions merge by `seq`, newest first, deduplicated and capped at 50.
- Empty decision metrics now show a clear explanatory note.
- Metrics table JSX is readable multi-line markup.
- Parser coverage includes captured metrics, escaped labels, comma-containing labels, `±Inf`, `NaN`, unlabeled samples, timestamps, and comments.
- Added browser spec 5 and same-context two-tab pipeline proof.
- Added drawer screenshots:
  - `drawer-1280x720.png` — 771 KB
  - `drawer-1920x1080.png` — 804 KB

Verification:

```text
Web Vitest: 38 → 42 passed, 2.81s
Backend: 411 passed, 9.43s, TOTAL 98%
make lint: PASS
make typecheck: PASS
make web-build: PASS
make web-e2e: 16 passed, 28.2s
```

The second `make web-e2e` was invoked in the clean-install regression command and exited successfully; its transcript was output-truncated after starting the passing run.

Real-server stop/sequence evidence:

```json
{"run_id":"64cd951c7d14430690b20e08dab4d35a","total":60,"status":"started"}
{"stopped":true}
[{"seq":3,"timestamp":"2026-09-27T06:58:38.812623Z", ... }]
[{"seq":3,"timestamp":"2026-09-27T06:58:38.812623Z", ... }]
```

The two decision responses, three seconds apart, retained `seq: 3`.

`jev_fhir_decisions_total` still had no captured samples after demo calls; the drawer now explains this rather than rendering an empty grid.

Could not complete exactly as requested:

- The sandbox rejected the explicit `rm -rf web/node_modules`; I ran `make web-install` (`npm ci`) instead.
- I did not add the controlled-server kill/restart Playwright test.
- I did not perform the requested seven planted-bug mutation runs or collect their failure summaries.
