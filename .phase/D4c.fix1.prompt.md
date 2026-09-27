D4c fix-up round 1. Same rules as before (AGENTS.md and .phase/D4c.prompt.md; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). No `src/` changes, no new dependencies. Finish every item
before you stop; if you can't, list exactly what is missing.

The evaluator ran the full final D4 regression from a clean `npm ci`: everything green (Vitest 60, backend 412, build,
fixtures deterministic, `make web-e2e` 28 passed twice). Planted bugs: 6 of 7 caught (the no-fixtures text, the runbook
fixture, reduced motion, a 1400 px card, never-stack, a `tokens.ts` colour). Problems:

## 1. The contrast test doesn't test the real CSS (❌)
`polish.test.tsx` checks `web/src/lib/tokens.ts`, which only "mirrors" `index.css`. Planted bug: `--c-review: #d49a00` in
**index.css** (light) → all 60 tests still pass. Make the test read the actual values from `web/src/index.css` (parse the
`:root` block and the dark-theme block), or generate the CSS variables from `tokens.ts` so there is one source. Then
changing a colour in the CSS must fail the test. Keep the printed ratio table.

## 2. Dark mode is unreadable in the JSON viewers (❌, seen in `studio-quality-dark-1280x720.png`)
In Raw FHIR and the Response / AuditEvent JSON (`JsonView`, @uiw/react-json-view), keys such as `resourceType`,
`identifier`, `jev_raw` are dark-on-dark and barely visible; the fixture search input is a bright white box. Give
`JsonView` a dark theme under `prefers-color-scheme: dark` (the library's CSS variables or its dark theme, via our
tokens) and style inputs/selects with the tokens. Extend the contrast test (or add an e2e check with
`colorScheme: "dark"`) so JSON key and value colours on their background are ≥ 4.5:1, and regenerate the dark screenshot.

## 3. Horizontal overflow at 900 px (❌, seen in `studio-quality-900x800.png`, captured 1001 px wide)
The TopBar doesn't fit below ~1000 px, so the page scrolls sideways. Let the TopBar wrap (e.g. nav on its own row) below
1024 px so there's no horizontal scroll at 900 px; add 900×800 to the no-horizontal-scroll e2e check (Studio and
Overview).

## 4. The runbook's live-mode instruction is wrong (❌)
`make demo` doesn't set `MOCK_JEV`; it comes from `.env`, and the committed `.env.example` (and a typical `.env`) has
`MOCK_JEV=true`. "start without that override" therefore starts **mock**. Write the exact commands: live =
`MOCK_JEV=false make demo` (after `make smoke-live`); fallback = stop it and `MOCK_JEV=true make demo`; check `/health`
shows `jev_client` `live` / `mock` and the badge. Say that the `.env` value is the default when no override is given.

## Planted bugs to re-run yourself (paste each failing line)
`--c-review: #d49a00` in index.css (light); a dark JSON key colour set to `#1d2939`; `width: 1400px` on `.top-bar` at
900 px (or removing the TopBar wrap rule); plus re-confirm the 6 already caught.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-types && git status --porcelain web/src/test/fixtures/          # clean
make web-test && make web-build && make web-e2e                          # all pass except D2a's intentional ✘; twice
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len
make lint && make typecheck && make test                                 # backend 412
```

## Report back with
Changed files; Vitest 60 → after; both `make web-e2e` summaries; the planted-bug failing lines; the updated contrast table
(incl. the JSON colours); anything not done, plainly at the end.
