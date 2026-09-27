Implemented the round-2 fixes.

Key changes:

- Drawer tests now cover:
  - polling interval creation before fake-time advancement and cleanup after close
  - pre-open request metadata and later request updates
  - Escape close
  - App/TopBar toggle and `aria-expanded`
  - Pipeline `connected` → `disconnected` EventSource state
- Drawer duration now uses `milliseconds()` and displays `ms`.
- Top bar is above the drawer (`z-index: 11`) so its toggle remains clickable.
- Decision JSON wraps safely; drawer has viewport-height scroll and bounded decision-log scrolling.
- Playwright drawer test now requires a UUID-shaped request ID observed from an API response; no empty-string fallback.
- Two-tab spec now uses the fixture page’s existing guarded context.

Changed files:

- [ObservabilityDrawer.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/shell/ObservabilityDrawer.tsx)
- [index.css](/home/budi/code/sphere_project/FHIR_JEV/web/src/index.css)
- [observability.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/observability.test.tsx)
- [pipeline.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/pipeline.spec.ts)
- [screenshots.spec.ts](/home/budi/code/sphere_project/FHIR_JEV/web/e2e/screenshots.spec.ts)

Verification completed:

```text
Vitest: 42 → 46 passed
Targeted drawer tests: 7 passed
npm run lint: PASS
npm run typecheck: PASS
make web-build: PASS
make lint: PASS
make typecheck: PASS
make test: 411 passed, TOTAL 98%
```

The first final e2e run passed all 16 specs, including the strengthened drawer and two-tab tests. The second invocation was started and progressed through screenshot generation, but the tool time limit cut its terminal transcript before its final summary; the server exited cleanly afterward.

Regenerated screenshots:

- `drawer-1280x720.png` — 772 KB
- `drawer-1920x1080.png` — 822 KB

They now show a full-height right slide-over with wrapped JSON, bounded log scrolling, contained tables, and a visible TopBar toggle above the drawer.

I could not complete the requested six destructive planted-bug mutation runs and collect their individual failing-summary lines before the usage limit interrupted work.