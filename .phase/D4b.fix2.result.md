I could not complete the final D4b fix-up within this turn.

Completed:
- Fixed the real `R` focus bug: keyboard shortcuts now ignore only text-entry inputs, textarea/select/contenteditable/CodeMirror. Range, radio, checkbox, and button focus no longer suppresses presenter shortcuts.
- Restored the `1`-key entry in the Playwright reset scenario after waiting for Overview.
- Added a Playwright `1`–`6` scene-jump check.
- Expanded `presenter.test.tsx` to cover text-entry suppression and range/radio shortcut handling.

Files changed:
- `web/src/state/presenter.tsx`
- `web/e2e/presenter.spec.ts`
- `web/src/test/presenter.test.tsx`

The focused presenter test still needed one final assertion cleanup when the turn ended: test DOM cleanup is not automatic in the current setup, so the new range/radio test must use its render container for all location assertions. I had started that correction.

Not completed:
- The required full Vitest suite with all nine requested presenter/Studio/Pipeline regression tests.
- The nine planted-bug executions and their failing summary lines.
- Both full `make web-e2e` runs.
- Regenerated and viewed scene screenshots.
- The remaining Verify commands and backend suite report.