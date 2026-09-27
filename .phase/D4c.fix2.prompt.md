D4c fix-up round 2 (the LAST allowed). Same rules as before. No `src/` changes, no new dependencies.
Do the items in order and don't stop until all are done.

Evaluator status after round 1: eslint and tsc pass; the TopBar wrap, token-styled inputs and the corrected runbook
commands (`MOCK_JEV=false make demo` / `MOCK_JEV=true make demo`) are in. But Vitest is RED: 1 failed / 59 passed:
`polish.test.tsx > keeps CSS decision tokens, JSON text, and tinted chips at AA contrast` →
`expected 1.455099857050875 to be greater than or equal to 4.5`.

## 1. Make the contrast test read the real CSS, then make it pass honestly
- The test must take its colours from `web/src/index.css` itself (import it with `?raw` and parse the `:root { … }` block
  and the `@media (prefers-color-scheme: dark) { :root { … } }` block into two maps of `--c-*` → hex), or `index.css`
  must be generated from `tokens.ts`. There must be ONE source: changing a colour in `index.css` must change the test.
  Delete `tokens.ts` if it is no longer the source.
- Pairs (both themes): each decision colour (`accept`, `review`, `flag`, `neutral`, `mock`, `live`) on `bg` and on
  `surface`; each chip colour on its `-tint`; `text` and `muted` on `bg` and `surface`; the JSON viewer key and value
  colours on the JSON background.
- The 1.46 failure is real: find which pair it is (print name + ratio in the assertion message) and fix the COLOUR in
  `index.css`, not the test. Never lower the 4.5 threshold or drop a pair.

## 2. Verify and planted bugs (paste the output)
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-types && git status --porcelain web/src/test/fixtures/          # clean
make web-test && make web-build && make web-e2e                          # all pass except D2a's intentional ✘
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
make lint && make typecheck && make test                                 # backend 412
```
Planted bugs (run each, confirm a failing test, restore exactly): `--c-review: #d49a00` in index.css (light); a dark JSON
key colour set to `#1d2939` in index.css; remove the TopBar wrap rule below 1024 px.

## Report back with
Changed files; Vitest 60 → after; the `make web-e2e` summary; the 3 planted-bug failing lines; which pair was 1.46 and
the colour change you made; the final ratio table; anything not done, plainly.
