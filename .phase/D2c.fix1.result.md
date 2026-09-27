Fixed the Studio visual contract gaps and regenerated screenshots.

Changed:

- [ScoreGauge.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/ScoreGauge.tsx) — SVG semicircular radial gauge, score-proportional arc, threshold tick, separate labels.
- [FixturePicker.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/FixturePicker.tsx) — visible fixture name plus secondary ground-truth label/tags.
- [ArtifactTabs.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/ArtifactTabs.tsx) — spaced active tabs, separate copy action, Response collapsed at depth 1.
- [VerdictStrip.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/VerdictStrip.tsx) — separated styled pills.
- [Studio.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/pages/Studio.tsx) — spaced module tabs with `aria-pressed`.
- [index.css](/home/budi/code/sphere_project/FHIR_JEV/web/src/index.css) — heading, gauge, picker, tab, artifact, and verdict styling.
- [studio.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/studio.test.tsx) — SVG mutation tests and visible-name/label picker assertion.

Verification:

- `make web-test`: 27 → 28 Vitest tests, all passed in `1.90s`; ESLint and TypeScript clean.
- `make web-build`: passed; largest non-map chunk is CodeMirror at `433.50 kB`.
- `make web-e2e`: 8 passed in `12.3s`; screenshots regenerated.
- Line-length command: no output.
- `make lint && make typecheck && make test`: passed; backend `408 passed` in `8.74s`, total coverage `98%`.
- Frontend per-file coverage: N/A; the configured Vitest suite has no coverage provider. The changed gauge and picker behavior have direct Vitest assertions.

`studio-quality-1280x720.png` now has a green semicircular 80/100 arc with a dark threshold-70 tick and separate threshold/confidence text. The fixture column leads with names such as `complete_patient`, with muted labels and tags beside them. The selected `quality` tab is dark/active; verdicts are distinct rounded pills; artifact controls are separated Response/AuditEvent tabs plus copy button.

Open question for evaluator: none.