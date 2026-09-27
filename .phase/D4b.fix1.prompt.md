D4b fix-up round 1. Same rules as before (AGENTS.md and .phase/D4b.prompt.md; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). No `src/` changes, no new dependencies. **Finish every item
before you stop**; if you can't, list exactly what is missing.

The evaluator reproduced D4b: lint, typecheck, build, backend 412, `make web-types` (catalog.json deterministic), Vitest 53
are green, and the scene walk e2e passes. But:

## 1. Two e2e failures (❌) — `make web-e2e`: 2 failed / 19 passed (ignore D2a's intentional guard ✘)
- **`R` resets the thresholds.** times out on `getByLabel('Quality threshold')`: the page snapshot shows it still on
  "Scene 0/6 · step 1/1 · Overview". The `1` key was pressed right after `goto`, before the presenter handler was
  attached. Wait for the app (e.g. the stepper or the Overview heading) before pressing keys, in every presenter test.
- **The D2 screenshots test** now fails at the Playground: `<aside class="presenter-notes">… intercepts pointer events` on
  "Load fixture as starting point". The notes preference turned on by the scene capture persists (localStorage), and
  the fixed bottom strip covers page content. **This is a real UI bug:** when notes are shown, the page must reserve
  space for the strip (e.g. bottom padding on `body`/`main` equal to the strip height) so no control is ever covered.
  Also make the screenshot spec turn notes off again after the scene capture.

## 2. Studio thresholds from the URL (❌, likely bug — verify and fix)
`Studio.tsx` reads URL thresholds only in the `useState(() => urlOverrides)` initializer. When the URL changes on the
same Studio route (the next step, e.g. `minimal_patient` → `complete_patient?quality_threshold=85`, or `R` re-applying
the same URL), the overrides must follow the URL; `R` must also clear a slider change even when the URL is identical.
Make the overrides derive from / resync with the URL on every navigation (without breaking manual slider use), and
cover both cases in tests.
Also: the Pipeline autostart `api(...)` promise has no `.catch` (an unhandled rejection if it fails): show the error with
`ErrorCard` or at least catch it.

## 3. Missing tests (❌): the evaluator planted 8 bugs; only 1 was caught (the fixture typo)
Add the tests the D4b prompt listed so each of these fails. Run each yourself, confirm the failure, restore the file
exactly, and report the failing summary line:

| Planted bug (evaluator ran it; tests stayed green) | Test that must catch it |
| --- | --- |
| `isTypingTarget` only checks `"input, select"` | keys ignored in textarea, `[contenteditable]`, and the CodeMirror editor (`.cm-content`), plus Ctrl/Meta held |
| `→` skips the last step (`position.step + 2 < count`) | `→` visits every listed state once, in order, across scenes (assert the URL/fixture/thresholds sequence); `←` walks back |
| `R` is a no-op | after a slider change, `R` restores the step's thresholds (Vitest and the e2e spec) |
| `F` sets "150" | `F` toggles `data-scale` 100 ↔ 125 exactly |
| `N` does nothing | `N` shows/hides the notes strip and persists; with a throwing localStorage it still toggles |
| Pipeline autostart without the `!connected` guard | autostart posts exactly one run, only after the stream connects, and clears the params |
| Studio ignores URL thresholds | Studio with `?quality_threshold=85` sends 85 in the compare overrides; without params, unchanged |
| (also) `O` | `O` toggles the drawer (same state as the TopBar button) |

## 4. Screenshots
After fixing item 1, generate `scene-quality-1280x720.png` / `-1920x1080.png` (Scene 1 with the stepper and notes visible)
and make sure the notes strip covers nothing important in them. The evaluator will view them.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-types && git diff --exit-code web/src/api/schema.d.ts && git status --porcelain web/src/test/fixtures/
make web-test && make web-build && make web-e2e                  # all pass except D2a's intentional ✘; run twice
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len          # nothing
make lint && make typecheck && make test                         # backend 412
git status --porcelain benchmarks/ src/                          # nothing
```

## Report back with
Changed files; Vitest 53 → after; both `make web-e2e` summaries; the 8 planted-bug failing lines; how the Studio URL
resync works; a short description of the scene screenshots; anything not done, plainly at the end.
