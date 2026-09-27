Implement Phase D4b — Scenes and presenter controls, from docs/Jev × FHIR — Demo Technical Implementation Plan.md.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2–D4a built every page; reuse them. D2a's
`web/src/state/uiPrefs.tsx` already holds `fontScale` (100/125, applied as `html[data-scale]`) and `presenterNotes`, both
persisted in localStorage inside try/catch: build on it, don't duplicate it. Keep the lessons:
- never obfuscate data to pass a check
- **finish the whole phase before you stop** (D3a, D3b and D4a first passes stopped early). Don't end your turn until every
  item below exists and the Verify block passes; if you truly can't, list exactly what is missing
- **run the planted bugs below yourself** and report each failing summary line (skipped in D3a–D4a)
- avoid vacuous tests (no `?? ""` in `toContain`, identical mock values, fake timers enabled too late)
- lines ≤ 100 chars; no `eslint-disable max-len`; don't reformat files you don't change
- the evaluator VIEWS the screenshots

Read before you start:
- the plan: "## Phase D4" → "How D4 Is Organised" (the scene fixtures are **provisional, from the mock full report**),
  "D4 Contract" Steps 3, 4 and 7, and "#### Phase D4b"
- docs/Jev × FHIR — Demo Plan Requirement.md §2 "Scene Flow" and "Scene Scripts" (the talk track for `note`) and UI-D-1…3

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies. No change to
`src/` (the backend). Never run live Jev.

## Scope (D4b only)

### 1. Catalog snapshot
`web/src/test/fixtures/catalog.json`: the committed list of catalog fixture ids (and module/source), generated from the
backend catalog, and refreshed by `make web-types` (extend that Makefile target and the existing
`scripts/dump_openapi.py`, or add a small script under `scripts/`; don't touch `src/`). Deterministic output.

### 2. `web/src/scenes.ts` (Step 3 interface exactly)
Scenes follow Demo Plan §2. Use these fixture ids (verified in the catalog and in the mock full report
`bench_20260927T120759Z`; cite that report name in a comment, and say for each choice why it shows the point: e.g.
`mixed_bundle` is wrong for both Jev and rules in the report; `dbd_text_only` is missed by both):
- **0 Overview** (`/`).
- **1 Quality** (`/studio/quality`): steps `tests/fixtures/patients/complete_patient.json` (auto-accept) →
  `tests/fixtures/patients/invalid_nik.json` (NIK gate → review) → `benchmarks/dataset/hard/patients/nik_dotted.json`
  (dotted NIK) → `tests/fixtures/patients/minimal_patient.json` (low score) → `complete_patient` with
  `{ quality_threshold: 85 }` (the control knob → review).
- **2 Router** (`/studio/router`): `tests/fixtures/bundles/lab_bundle.json` → `tests/fixtures/bundles/immunization_bundle.json`
  → `tests/fixtures/bundles/mixed_bundle.json` → `mixed_bundle` with `{ route_confidence_minimum: 0.99 }` (→ unknown).
- **3 Notifiable** (`/studio/notifiable`): `tests/fixtures/conditions/japanese_encephalitis_a83.json` (Flag + Dinkes) →
  `tests/fixtures/conditions/common_cold_j06.json` → `benchmarks/dataset/hard/conditions/dbd_text_only.json` (hard case).
- **4 Pipeline** (`/pipeline`): `autoAction: "startPipeline"`, `pipeline: { source: "unit", ratePerS: 4 }` (the unit set is
  60 resources, not the Demo Plan's "50"; say so in the note or a comment).
- **5 Benchmarks** (`/benchmarks`).
- **6 What's next** (`/`, architecture; note about the LLM reasoning layer).
`note` = the scene's talk track (short, from the Scene Scripts). Top-level `fixtureId` / `thresholds` = the scene's first
state; `steps` = the sub-steps after it (or model it so that `→` visits every listed state exactly once, in order; say
how).

### 3. Applying a scene (Step 4: "navigates, sets the fixture and thresholds, and runs autoAction")
- **Thresholds via the URL.** Studio keeps threshold overrides in local state today. Make Studio also read overrides from
  query params (e.g. `?fixture=…&quality_threshold=85`, names = `Thresholds` keys), so a scene (and a deep link) sets
  them. Slider changes still work; existing Studio behaviour and tests stay unchanged when no params are present.
- **startPipeline:** the run must start only after the Pipeline page is mounted and its SSE stream is open (otherwise it
  misses the `started` event). E.g. navigate to `/pipeline?autostart=1&source=unit&rate=4`, and have the Pipeline page
  start once connected, then drop the params (replace) so a reload doesn't restart it.
- **R** re-applies the current scene/step exactly (fixture + thresholds, including clearing slider changes).

### 4. Presenter controls (Step 4)
- One global key handler (e.g. `web/src/state/presenter.tsx` with a provider in `App`), **ignored when focus is in an
  input, select, textarea, contenteditable, or the CodeMirror editor**, and when a modifier key (Ctrl/Meta/Alt) is held.
- `→` next step, or next scene after the last step; `←` previous; `1`–`6` jump to that scene (step 1); `R` reset;
  `F` font scale 100 ↔ 125 (via uiPrefs); `O` toggles the observability drawer (lift the drawer state so both the TopBar
  button and `O` control it); `N` toggles presenter notes. Scene 0 is reached with `←` from 1 (or `0` if you add it).
- **SceneStepper** in the TopBar (replace the "Scene stepper placeholder" span): `Scene n/6 · step m/k`, plus the scene
  title; accessible labels.
- **Notes strip** at the bottom showing the current `note` (off by default, toggled by `N`, persisted via uiPrefs).
- Only the handler's own scene state drives navigation; don't break normal clicking around (manual navigation is fine;
  the stepper may show the last applied scene).

## Tests
Vitest (titles verbatim from Step 7 where they apply):
- "Every `SCENES[*].fixtureId` and step fixture exists in a committed catalog snapshot" (reads `catalog.json`).
- "The key handler ignores keystrokes inside inputs." (input, textarea, select, contenteditable, and the CodeMirror
  editor or its `.cm-content`), and with Ctrl/Meta held.
- `→`/`←` order across scenes and steps (every listed state visited once, in order; `←` goes back); `1`–`6`; `R` restores
  the current step's thresholds after a slider change; `F` toggles `data-scale`; `O` toggles the drawer; `N` toggles
  notes and persists (with a localStorage that throws: still works).
- Studio reads threshold overrides from the URL; without params it behaves as before.
- The Pipeline autostart starts exactly one run, only after the stream is connected, and clears the params.

Planted bugs (run each, confirm a test fails, restore exactly, report the failing summary line): the handler forgets to
ignore textarea/CodeMirror; `→` skips the last step of scene 1; `R` doesn't clear a slider change; `F` sets 150; `N` not
persisted; a scene fixture id typo; autostart fires before the stream connects; Studio ignores the URL threshold.

Playwright (titles verbatim from Step 7; new file e.g. `web/e2e/presenter.spec.ts`, serial, the auto network guard stays):
3. "Pressing `→` from Overview walks scenes 0 through 6 with no manual input, and each scene's key element is visible."
   (assert per scene/step: the URL, the selected fixture, the key element — e.g. `lane` for Studio, the Flag tab for JE,
   `review_needed` at threshold 85, `unknown` at floor 0.99, the pipeline run status "running"/"finished", the Benchmarks
   heading/disclaimer, the architecture diagram)
4. "`R` resets the thresholds."
5. "`F` changes the root font size." (computed `font-size` of `html` changes)
6. "The network guard (no external hosts) covers the whole walk." (the walk runs with the guard active; no blocked URLs)
Also: typing `R`, `F`, `→` inside the Playground editor does not trigger them; no console errors during the walk.
Add screenshots of Scene 1 with the stepper and the notes strip visible (`scene-quality-<w>x<h>.png`, both sizes).

## Out of scope
D4c polish (contrast, reduced motion, empty states, runbook). No backend (`src/`) changes.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-types && git diff --exit-code web/src/api/schema.d.ts   # catalog.json regenerated deterministically
make web-test && make web-build && make web-e2e                  # run make web-e2e twice
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len          # nothing
make lint && make typecheck && make test                         # backend 412
git status --porcelain benchmarks/ src/                          # nothing
```

## Report back with
Everything AGENTS.md's "Final message" asks for (before: backend 412, Vitest 51, Playwright 19), plus the output of every
Verify command, the failing summary line for each of the 8 planted bugs, how steps/`→` order is modelled, the screenshot
files with sizes and a short description, and anything you couldn't do, stated plainly at the end.
