D4b fix-up round 2 (the LAST allowed). Same rules as before. No `src/` changes, no new dependencies.
Work in this order and don't stop until all four parts are done: **1 → 2 (tests) → 3 → 4 (verify)**. Tests are the
main job; last round none of them were added.

Round 1 status (evaluator-verified): notes padding, the screenshot notes toggle, the autostart `.catch`/ErrorCard and the
Studio URL resync are in. The evaluator reverted `web/src/test/fixtures/compare_notifiable.json`: it only changed because
`make web-types --samples` stamps today's date into the sample Flag (pre-existing; recorded; don't commit that diff —
restore it with `git checkout -- web/src/test/fixtures/compare_notifiable.json` if `make web-types` changes it again).

## 1. The `R` bug (❌, real demo bug)
`make web-e2e`: "`R` resets the thresholds." still fails: after `fill("85")` and `R`, the slider stays at 85. Cause:
focus remains on the range slider, and `isTypingTarget` treats every `input` as typing, so `R` is ignored right after a
threshold change — exactly when a presenter presses it. Only **text entry** should block the shortcuts: `textarea`,
`select`, `[contenteditable]` / `.cm-content`, and `input` whose type is text-like (text, search, email, number,
password, url, tel, or no type). Range sliders, radios, checkboxes and buttons must NOT block them.
Also restore the `R` e2e test so it enters Scene 1 with the `1` key again (after waiting for the Overview), instead of `→`,
and add a separate e2e check that `1`–`6` jump to the right scene.

## 2. Vitest (❌): add these in `web/src/test/presenter.test.tsx`. Each must fail under its planted bug.
Run every planted bug yourself, confirm the failure, restore the file exactly, and paste the failing summary line.

| Planted bug | Test |
| --- | --- |
| `isTypingTarget` only checks `"input, select"` | keys ignored in a textarea, a `[contenteditable="true"]` div and a `.cm-content` element; ignored with Ctrl/Meta |
| `isTypingTarget` blocks every input (today's bug) | `R` / `→` still work when focus is on a range input or a radio |
| `→` skips the last step (`position.step + 2 < count`) | pressing `→` from scene 0 visits every scene/step state once, in order (assert the router location sequence: path + `fixture` + threshold params); `←` walks back |
| `R` is a no-op | after `→` into a step with a URL threshold and a slider change, `R` re-applies the step (location + Studio override) |
| `F` sets "150" | `F` toggles `document.documentElement.dataset.scale` 100 ↔ 125 |
| `N` does nothing | `N` shows/hides the notes strip; the preference persists; with a throwing localStorage it still toggles |
| `O` does nothing | `O` toggles the drawer (the same state the TopBar button uses) |
| Pipeline autostart without the `!connected` guard | with a mocked EventSource: no POST before `onopen`; exactly one POST after; the autostart params are cleared |
| Studio ignores URL thresholds | Studio at `?fixture=…&quality_threshold=85` sends `quality_threshold: 85` in the compare body; without params it sends none |

Use a real `MemoryRouter` + the providers (see `observability.test.tsx`'s App test for the pattern) and read the location
via a small probe component.

## 3. Screenshots
`make web-e2e` must regenerate `scene-quality-1280x720.png` / `-1920x1080.png` (Scene 1 with the stepper and notes strip).

## 4. Verify (paste real output)
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e                  # all pass except D2a's intentional ✘; run twice
git checkout -- web/src/test/fixtures/compare_notifiable.json 2>/dev/null; git status --porcelain web/src/test/fixtures/
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len          # nothing
make lint && make typecheck && make test                         # backend 412
```

## Report back with
Changed files; Vitest 53 → after; both `make web-e2e` summaries; the failing line for each of the 9 planted bugs; anything
not done, plainly at the end.
