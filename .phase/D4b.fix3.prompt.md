D4b fix-up round 3 (approved by Budi as an exception). Same rules as before. This round is SMALL: only the items below,
in `web/src/test/`, `web/e2e/` and nothing else unless a test exposes a real bug. No `src/` changes.

The evaluator re-ran everything after round 2: all gates green, `make web-e2e` 24 passed twice, and 7 of 10 planted bugs
are caught (by Vitest or e2e). Three planted bugs still leave EVERY test green:

| Planted bug (in `web/src/state/presenter.tsx`) | Add a test that fails under it |
| --- | --- |
| `element.closest("textarea, select, [contenteditable='true'], .cm-content")` → `element.closest("select")` | Vitest: keydown `r`, `f`, `ArrowRight` dispatched from a focused `textarea`, a `[contenteditable="true"]` div and an element inside `.cm-content` change nothing (location, `data-scale`). AND the checklist item "Key handler ignores keys typed in Playground editor": a Playwright test that focuses the Playground CodeMirror editor, types `r`, `f` and presses `ArrowRight`, and asserts the text was typed into the editor, the URL is still `/playground`, and `html[data-scale]` didn't change |
| `setPresenterNotes(!presenterNotes)` → `void presenterNotes` | `N` shows the notes strip with the current scene's note, a second `N` hides it (Vitest or e2e) |
| `onDrawer()` → `void onDrawer` | `O` opens the observability drawer and a second `O` closes it (Vitest with the App, or e2e) |

Also fix the scene screenshot capture in `web/e2e/screenshots.spec.ts`: it waits only for the stepper text, so the
Scene 1 screenshot shows an empty decision column and no notes strip. Wait for the decision (`getByTestId("lane")`) and
for the notes strip to be visible before capturing, then turn notes off again.

Run each of the 3 planted bugs yourself, confirm a test fails, restore the file exactly (`git diff` must show no change
to `presenter.tsx` afterwards), and paste the failing summary line.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e       # all pass except D2a's intentional ✘
git checkout -- web/src/test/fixtures/compare_notifiable.json 2>/dev/null
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len
```

## Report back with
Changed files; Vitest 54 → after; the `make web-e2e` summary; the 3 planted-bug failing lines; anything not done.
