Fix two e2e tests that fail whenever a live benchmark report is the newest one. Follow AGENTS.md
(standing rules). Finish the whole task before you stop, including the planted checks.

## Problem

`web/e2e/benchmarks.spec.ts:7` and `web/e2e/screenshots.spec.ts:9` assert the mock disclaimer on the
report the page opens with. The page opens on the newest report, and the newest one is now the untracked
live report `bench_20261031T150439Z`, which has no disclaimer. Real behaviour is correct; the tests
wrongly assume the newest report is always mock. Each future live run would break them again.

## Scope (these two files only)

1. `web/e2e/benchmarks.spec.ts`, first test:
   - Keep proving that the page opens on the latest report: assert the `Benchmark report` select's value
     equals its first option's value, read from the page. Don't hard-code a report name for this. First
     confirm from the code that the first option is the newest, and say how you confirmed it.
   - Then `selectOption("bench_20260927T120759Z")`, the committed mock full report, before the disclaimer
     and `FAIL · Routing accuracy ≥ 90%` assertions.
   - Keep the rest of the test, including the `bench_20260924T151507Z` step and its `73%` assertions.
     Reword the title only if it no longer describes the test.
2. `web/e2e/screenshots.spec.ts`, the `benchmarks` capture: select `bench_20260927T120759Z` before the
   disclaimer assertion, and wait for the disclaimer as it does now.

**Never remove or relax an assertion.** If the pinned report doesn't satisfy one, stop and explain.

## Must not change

Everything else. In particular `web/src/` (it has the owner's uncommitted edits),
`benchmarks/results/*`, `web/video/`, `docs/`, the backend, and `web/playwright.config.ts`. Don't move,
rename or delete any benchmark report. Don't use `git checkout`, `git restore`, `git stash`, `git reset`
or `git clean`. Don't commit. Mock Jev only; never run a live command or read `.env`.

## Verify (real output)

Node: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. Backend gate before you start: 456 tests.

1. `npm run lint`, `npm run typecheck`, `npm run test` in `web/`.
2. **With the live report present:** `npm run e2e`. Must be 29 passed.
3. **Without it:** copy only the git-tracked reports (`git ls-files benchmarks/results`) to
   `web/test-results/committed-reports/`, then run `npm run e2e` with `demo_results_dir` pointed there.
   Check `src/jev_fhir/config.py` for the exact environment variable. Must be 29 passed. This proves the
   tests don't depend on the untracked report. Show that the override really took effect, for example by
   confirming the live report isn't listed in that run.
4. **Planted checks, in the spec files only, because `web/src` must stay untouched:** copy the spec aside,
   record `sha1sum`, plant, run that one test, paste the FAILED line, restore, and show matching hashes.
   a. In `benchmarks.spec.ts`, select `bench_20261031T150439Z` instead of the mock report: the disclaimer
      assertion must fail.
   b. In `benchmarks.spec.ts`, compare the select's value to a wrong report name: the latest-report
      assertion must fail.
5. Report any tracked file under `web/e2e/screenshots/` that the runs changed. Don't revert them.
6. `git status --porcelain`, and confirm no server is left running.

## Report back

The changed files, the output above, how you confirmed report ordering, and any question for the
evaluator.
