D2a fix-up round 1. Same rules as before (AGENTS.md and the D2a prompt; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). Change only what's listed here.

The evaluator reproduced D2a: backend 408 green; clean `npm ci`; `make web-test` 12/12; `make web-types` deterministic;
the build is under 1 MB per file; `make demo` serves /demo with the SPA fallback; `make web-*` works with NO node on the
PATH (NODE_BIN); and 5/5 planted bugs in the unit-tested code were caught. Three problems remain:

## 1. Don't obfuscate data to pass a check (scripts/dump_openapi.py, around line 25)
`_write_json` rewrites `http://` to `http://` in the recorded samples so that
`grep -rn "http://\|https://" web/src` finds nothing. The decoded data is the same, but obfuscating data to satisfy
a check defeats the check, and it isn't acceptable.
- Remove that replacement. Write the samples as normal readable JSON (`json.dumps(..., indent=2, sort_keys=True)` +
  trailing newline), keeping the determinism (fixed latency and timestamps).
- The URLs in them are FHIR code-system identifiers (e.g. `http://snomed.info/sct`), data that is never fetched. The
  evaluator records those grep hits as such. Don't move, rename or re-encode anything to hide them.
- Regenerate with `make web-types`; `git status` must then show the samples as plain JSON.

## 2. The network guard must actually guard every test (web/e2e/fixtures.ts, web/e2e/overview.spec.ts)
Evaluator's mutation: with the guard disabled (`if (false) {` in place of the host check), BOTH Playwright tests
still PASS. Two reasons:
- The guard is a regular fixture (`requests`), so it's only installed in specs that ask for it. The second test only
  uses `page`, so no guard runs there at all.
- That test fetches `https://example.invalid/`, which fails regardless (`.invalid` never resolves), so it proves
  nothing about the guard.

Fix:
- Make the guard an **automatic** fixture (`{ auto: true }`) that is installed for every test. It records every
  request and blocks (aborts) any request whose host isn't `127.0.0.1` or `localhost`. It FAILS the test in the
  fixture teardown (after `use`) when anything was blocked, listing the blocked URLs. Don't throw from inside the
  route handler.
- Replace the guard test with one that proves the guard itself: request an external URL (e.g.
  `fetch("http://example.com/")` from the page) and assert the guard recorded and blocked it. Expose the blocked list
  through a fixture, or use `test.fail()` so the guard's teardown failure is the expected outcome. It must not rely on
  DNS failing.
- Done means: with the evaluator's mutation (the host check disabled), the guard test FAILS; with the real guard, both
  tests pass, and spec 1 still passes with the guard active automatically.

## 3. Readable formatting (all hand-written files under web/)
Many files are crammed onto very long single lines (e.g. `queries.ts` up to 297 chars; the shell components, uiPrefs,
the e2e fixture/spec and `playwright.config.ts` 170–250 chars). That's hard to review, and unlike the rest of the repo
(Python uses a 100-char limit).
- Reformat every hand-written `.ts` / `.tsx` / config file in `web/` to normal multi-line code with lines ≤ 100 chars.
  Excluded: the generated `src/api/schema.d.ts`, and the JSON samples.
- Add the ESLint core `max-len` rule (code 100, `ignoreStrings`, `ignoreTemplateLiterals`, `ignoreUrls`,
  `ignoreRegExpLiterals`) to `eslint.config.js`, ignoring `schema.d.ts`, so `npm run lint` enforces it. No new
  dependencies.
- Pure formatting: no behaviour change, no removed or weakened test assertions.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-types && make web-test && make web-build && make web-e2e
grep -c 'u002f' web/src/test/fixtures/*.json                    # 0 in every file
awk 'length > 100' $(git ls-files -o --exclude-standard web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)   # nothing
make lint && make typecheck && make test                          # backend still 408
```
Also run the guard mutation yourself (disable the host check), confirm the guard test FAILS, and restore the file.

Report back with the changed files, the web test counts, and, for the guard mutation, the Playwright line showing the
guard test failing under it.
