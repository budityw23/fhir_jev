I’m sorry, but this fix-up is not complete.

Implemented:
- Dark JSON viewer token styling and token-based input/select styling.
- TopBar wraps below 1024px; added 900px Overview/Studio overflow coverage.
- Corrected runbook commands: `MOCK_JEV=false make demo` for live, `MOCK_JEV=true make demo` for fallback, with `/health`/badge checks.
- Began contrast-test refactor and added JSON contrast tokens.

Incomplete:
- The contrast test still does not successfully parse real `index.css`; it remains tied to `tokens.ts`, so it does not meet the evaluator requirement.
- I did not complete the requested planted-bug runs or final Verify suite.
- I did not regenerate and inspect the dark screenshot after the JSON styling change.
- The last typecheck had a TypeScript signature error in `polish.test.tsx`; I patched its signature immediately afterward but did not get time to rerun validation.

Please treat this as unfinished work.