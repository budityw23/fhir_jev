I did not complete the requested fix-up round.

Completed fixes:
- Reserved bottom space while presenter notes are visible, preventing the fixed strip from covering controls.
- Screenshot capture now turns notes back off after the Scene 1 capture.
- Presenter e2e tests now wait for Overview before sending keys; the reset test uses `→` to enter Scene 1.
- Studio overrides now track the current query string during render, preserving manual slider changes until navigation changes the URL; a scene navigation or reset therefore restores URL-provided thresholds.
- Pipeline autostart now catches `ApiError` failures and renders `ErrorCard`.

Changed files:
- `web/src/pages/Studio.tsx`
- `web/src/pages/Pipeline.tsx`
- `web/src/index.css`
- `web/e2e/presenter.spec.ts`
- `web/e2e/screenshots.spec.ts`

Verification:
- `npm run lint`, `npm run typecheck`, and Vitest: 53/53 passed.
- Initial `make web-e2e`: scene walk passed; reset still failed before I changed its entry key to `→`. The run was interrupted before the amended spec could be rerun.
- Backend verification from the prior round remained green: 412 passed, 98% coverage.

Missing:
- Full presenter unit coverage for every planted regression, including textarea/contenteditable/CodeMirror, state sequence, R/F/N/O persistence, autostart sequencing, and URL threshold behavior.
- Both complete `make web-e2e` runs after the final change.
- Generated and reviewed Scene 1 screenshots.
- The eight planted-bug executions and failing summary lines.
- Full Verify command output and real-server curl output.