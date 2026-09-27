D2c fix-up round 2 (the last allowed). Same rules as before. Change only ScoreGauge.tsx, FixturePicker.tsx, and their
tests in studio.test.tsx.

Round 1 worked for the picker names, tabs, pills and artifacts (the evaluator viewed the new screenshot). Two problems:

## 1. The ScoreGauge threshold tick is not visible (❌)
In the regenerated `studio-quality-1920x1080.png`, the green arc shows 80 but there is NO visible tick at 70.
- Cause: the tick is a line at the arc's right end rotated by `rotate(180 - threshold * 1.8, 100, 100)`. In SVG, positive
  rotation is CLOCKWISE (y points down), so the tick is rotated BELOW the centre (off the visible upper arc and outside the
  `0 0 200 140` viewBox). At threshold 70 it lands around (147, 165).
- Fix: place the tick ON the upper arc. For example, compute it directly: θ = π·(1 − threshold/100); the outer point is
  (100 + r·cos θ, 100 − r·sin θ) and the inner point uses a smaller r. Or use the equivalent counter-clockwise rotation.
  Threshold 0 must sit at the left end, 50 at the top, 100 at the right end.
- Test (replace the weak "angle changes" assertion with a geometric one; don't drop other assertions): for threshold 70
  the tick's endpoints are ABOVE the centre (y < 100), to the RIGHT of centre (x > 100), and within about 2 px of the
  expected point on the arc. Threshold 50 is at the top (x ≈ 100). Threshold 0 is at the left end. This test must FAIL
  with the current clockwise rotation.

## 2. Duplicate fixture names in the picker (⚠️)
In the quality picker, `generated_000` … `generated_009` appear twice: generated Patients and generated Observations share
file names in different folders, so they can't be told apart.
- When two entries in the same list share a `name`, show the resource type as part of the visible name, e.g.
  `generated_003 · Patient` and `generated_003 · Observation`.
- Keep each radio's accessible name unchanged when it's unique. For duplicates it may include the resource type.
- Test: the visible labels of two same-name entries differ.

Verify: `make web-test && make web-build && make web-e2e` (screenshots regenerate), the line-length check, and backend
`make lint && make typecheck && make test`. Report the tick's endpoint coordinates for thresholds 0, 50 and 70 from your
test.
