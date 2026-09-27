Implementation is incomplete; I stopped short of claiming Phase D4b done.

Completed:
- Added `web/src/scenes.ts` with all seven scenes, ordered substeps, provisional-report rationale, and talk tracks.
- Added presenter provider, global keyboard controls, notes strip, TopBar stepper.
- Added URL threshold parsing in Studio and SSE-gated Pipeline autostart.
- Added deterministic catalog generation in `make web-types`.
- Added catalog/key-ignore Vitest coverage and presenter Playwright coverage.
- Added screenshot capture definitions for `scene-quality-1280x720.png` and `scene-quality-1920x1080.png`.

Validation that passed:
- `make web-types`
- `make web-test`: 53 Vitest tests passed
- `make web-build`
- `make lint`
- `make typecheck`
- `make test`: 412 passed, 98% backend coverage

Changed/added files include:
- `scripts/dump_openapi.py`
- `web/src/scenes.ts`
- `web/src/state/presenter.tsx`
- `web/src/App.tsx`, `main.tsx`, `pages/Studio.tsx`, `pages/Pipeline.tsx`
- `web/src/components/shell/TopBar.tsx`, `index.css`
- `web/src/test/fixtures/catalog.json`, `web/src/test/presenter.test.tsx`
- `web/e2e/presenter.spec.ts`, `web/e2e/screenshots.spec.ts`

What remains:
- Re-run and pass the full Playwright suite twice. The newly added scene-walk test initially had one off-by-one assertion; I corrected it but did not get to rerun it.
- Generate and visually inspect the requested screenshots.
- Run all eight planted-bug checks and report their failing summary lines.
- Run the required real-server curl checks. The final curl attempt could not connect because the temporary e2e server had exited.
- Run the exact long-line and `eslint-disable max-len` verification commands.