Implemented the final D2c fix-up within the allowed files:

- [ScoreGauge.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/ScoreGauge.tsx)
- [FixturePicker.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/components/studio/FixturePicker.tsx)
- [studio.test.tsx](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/studio.test.tsx)

The threshold tick now uses direct upper-arc geometry, not SVG rotation. Tested outer endpoint coordinates:

- Threshold 0: `(20, 100)` — left endpoint
- Threshold 50: `(100, 20)` — top
- Threshold 70: `(147.02, 35.28)` — upper-right arc

The test retains score arc assertions and verifies the tick is upper-right at 70, changes at 85, reaches top at 50, and left at 0. Duplicate fixture names now visibly include their resource type, e.g. `generated_003 · Patient` / `generated_003 · Observation`; unique accessible names remain unchanged.

Verification:

- `make web-test`: 28 → 28 Vitest tests, all passed in `1.93s`.
- `make web-build`: passed; largest non-map asset `433.50 kB`.
- `make web-e2e`: 8 passed in `12.2s`; screenshots regenerated.
- Line-length command: no output.
- `make lint && make typecheck && make test`: passed; backend `408 passed` in `8.59s`, 98% coverage.
- No backend files changed. Frontend coverage remains N/A because Vitest coverage is not configured.

Open question for evaluator: none.