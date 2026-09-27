D2c fix-up round 1. Same rules as before (AGENTS.md; Node 20 via `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`).
This round may touch the D2b Studio components listed below, because the D2c final checklist requires "Final code matches
the full D2 contract (Steps 1–11)". No backend changes; no new dependencies.

The evaluator reproduced D2c:
- gates green from a clean `npm ci` (Vitest 27, Playwright 8, build < 1 MB, backend 408)
- the Playground is correct, and 5/5 planted Playground bugs are caught
- the Overview screenshot looks right
But LOOKING at the Studio screenshot (`web/e2e/screenshots/studio-quality-1280x720.png`) shows problems no test catches.

## 1. ScoreGauge must be a radial gauge (❌, contract deviation)
The Step 8 table says `ScoreGauge` is a "0–100 radial gauge with a threshold tick". It currently renders a horizontal bar,
and its text runs together ("80/100threshold 70confidence 71%").
- Implement it as an inline SVG radial/arc gauge (e.g. a 180° or 270° arc):
  - the filled arc proportional to `score` / 100
  - a clearly visible tick at `threshold` / 100 on the arc
  - the score number in the centre, with separate, readable lines for "threshold N" and "confidence X%"
- Keep the props `{ score, threshold, confidence }` exactly.
- Vitest: the SVG arc length/angle for score 80 differs from score 20, and the threshold tick's angle changes when
  `threshold` changes from 70 to 85. Assert on the rendered SVG attributes, so the test fails if the gauge goes back to a
  bar or ignores the threshold.

## 2. FixturePicker must show the fixture name (❌, the Studio isn't operable by a presenter)
About 70 radio items show only the label ("auto_accept · 70–100 · NIK ✓"), so identical labels can't be told apart. The
tests only pass because they select by a hidden accessible name.
- Each item shows the fixture **name** (e.g. `complete_patient`) as its primary visible text, with the ground-truth label
  and the hard / draft tags as secondary text next to it.
- Keep each radio's accessible name exactly as it is now (the e2e specs use `getByLabel("complete_patient", { exact: true })`).
- Vitest: the visible text of an item contains its fixture name AND its label.

## 3. Readable layout and spacing (⚠️, cheap now; D4 does the full polish)
From the screenshot, text runs together with no spacing:
- Studio module tabs ("qualityrouternotifiable") → spaced tab buttons with a visible active state (`aria-current` or
  `aria-pressed`) for the current module
- VerdictStrip → three separated, styled pills
- ArtifactTabs ("ResponseAuditEventcopy") → spaced tab buttons with an active state, plus a separate copy button; show the
  Response JSON collapsed to depth 1 by default
- page headings ("Overview", "Studio", "Playground") styled as headings
Use the existing design tokens in `index.css`. Keep colour paired with icon or text. No behaviour changes: the existing
tests must keep passing unchanged.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e      # screenshots regenerated
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)                    # nothing
make lint && make typecheck && make test                                                  # backend 408
```
Report back with the changed files, Vitest before (27) → after, and a short description of the new
studio-quality-1280x720.png (what the gauge, picker, tabs and verdict pills look like). The evaluator will view the
screenshots.
