Partially completed.

Changed:
- `web/src/test/presenter.test.tsx`
- `web/e2e/screenshots.spec.ts`

Added Vitest coverage for:
- textarea, contenteditable, and nested `.cm-content` shortcut suppression;
- `N` showing/hiding notes;
- `O` toggling drawer state;
- retained range/radio shortcut handling.

Also updated Scene 1 screenshot capture to wait for the decision lane and notes strip.

Verification completed:
- `make web-test`: 56 Vitest tests passed (54 → 56 in the evaluator baseline; two additional presenter tests).
- `make web-build`: passed.
- `make web-e2e` began with 24 tests and all displayed tests passed except the intentional D2a network-guard test; the command was interrupted before its final summary.

Not completed:
- Required Playground CodeMirror Playwright test.
- Running each of the three planted mutations and recording their failing lines.
- Completing `make web-e2e` and the remaining verification commands.