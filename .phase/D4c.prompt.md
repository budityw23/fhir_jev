Implement Phase D4c — Polish, runbook, final D4 regression, from
docs/Jev × FHIR — Demo Technical Implementation Plan.md. This is the last D4 sub-phase.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2–D4b built every page, the drawer, scenes and
presenter keys. Keep the lessons:
- never obfuscate data to pass a check
- **finish the whole phase before you stop.** Every earlier first pass stopped early. Don't end your turn until every
  item below exists and the Verify block passes; if you truly can't, list exactly what is missing
- **run the planted bugs below yourself** and paste each failing summary line (you have skipped this every phase)
- tests must fail when their behaviour is removed; wait for the app before pressing keys in e2e
- lines ≤ 100 chars; no `eslint-disable max-len`; don't reformat files you don't change
- the evaluator VIEWS the screenshots

Read before you start:
- the plan: "## Phase D4" → "How D4 Is Organised", "D4 Contract" Steps 5, 6 and 7, "#### Phase D4c" and the **Final D4
  checklist**
- docs/Jev × FHIR — Demo Plan Requirement.md: UI-NFR-1…6, §2 (scenes), §6 (Demo Day Checklist), "Demo Risk Plan"
- `web/src/scenes.ts` (the scenes and key presses the runbook must match)

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies. No change to `src/`
(the backend). Never run live Jev (`make bench-live*`, `make smoke-live`).

## Scope (D4c only)

### 1. Step 5 polish (UI-NFR-*)
- **Layout:** no horizontal scroll on every page (Overview, each Studio module, Playground, Pipeline after a run,
  Benchmarks, and a page with the drawer open) at 1280×720 and 1920×1080. Studio columns stack below 1024 px (UI-NFR-2).
- **Contrast (WCAG AA 4.5:1):** the decision colours (`--c-accept`, `--c-review`, `--c-flag`, `--c-neutral`,
  `--c-mock`, `--c-live`) as text on `--c-bg` and `--c-surface`, AND the chip text on its tinted chip background (lane
  chips, PRD chips, mode badge, verdict pills), in **both** light and dark themes. Compute the ratios; adjust tokens that
  fail (keep the hues recognisable). Charts currently hard-code light-mode hex colours (`#16803c`, `#667085`, `#b42318`):
  use the tokens (`var(--c-…)`) so dark mode works.
- **Reduced motion:** honour `prefers-reduced-motion: reduce` everywhere there is motion (the architecture animation,
  the drawer slide, any transitions/smooth scrolling).
- **Empty states:** "no report yet" (Benchmarks, exists) and "no fixtures match" (a fixture search with no results);
  also give the Benchmarks breakdown and calibration sections a short empty message when a report has no rows for them
  (today they render bare headers).
- **ErrorCard on every `ApiError` path:** audit every `api()` / `apiText()` / query hook caller; any path that swallows
  an `ApiError` or shows nothing must render `ErrorCard` (list the callers you checked in the report).

### 2. Known polish from earlier phases (recorded in progress.md)
- The Studio fixture picker lists every fixture and makes Studio pages ~4000 px tall: put it in a bounded, scrollable
  box (e.g. max-height ~60vh) with the selected item scrolled into view; search still works.
- The TopBar wraps to two lines at 125 % font scale: keep it on one line at 1280 px wide and 125 % (compact spacing,
  shorter stepper text, or wrap only the nav — your choice, readable).
- Benchmarks latency cells wrap "33.3 / ms": keep value and unit together.
- `make web-types --samples` stamps today's date into `web/src/test/fixtures/compare_notifiable.json` (the Flag's
  `period.start`), so the sample changes every day. Make the sample generation deterministic in `scripts/` only (e.g.
  freeze the clock or normalise that one volatile field with a clear comment); don't change `src/`.

### 3. Step 6: `docs/demo-runbook.md` (one page)
From Demo Plan §6 and the Risk Plan: cold start (`make demo`), the mode switch (`MOCK_JEV`, live key in `.env` only,
`make smoke-live` before a live demo), the fallback (kill the live server, restart with `MOCK_JEV=true`, back on the
scene in < 30 s, exact commands), per-scene key presses and the expected screen (generated from / matching
`scenes.ts`: scene, step, fixture, what to point at), presenter keys (`← → 1–6 R F O N`), the Demo Day checklist, and
short Q&A answers ("why not just rules?", "how is confidence calibrated?", "what data does Jev see?", "PHI?"). Say the
scene fixtures are provisional (mock full report) and must be re-checked after `make bench-live-full`. Add a Vitest
that fails if a scene/step fixture in `scenes.ts` is missing from the runbook.

## Tests
- e2e (new file e.g. `web/e2e/polish.spec.ts`): the no-horizontal-scroll check for every page listed above at both sizes
  (`document.documentElement.scrollWidth <= innerWidth`); Studio stacks at 900 px width (columns' x positions equal);
  with `page.emulateMedia({ reducedMotion: "reduce" })` the architecture edge has no running animation.
- Vitest: a contrast test that reads the token values for light and dark (parse `index.css` or a shared token module)
  and asserts every pair above ≥ 4.5 (print the ratios); "no fixtures match"; the Benchmarks empty-section messages; an
  ErrorCard test for any path you fixed; the runbook ↔ scenes test.
- Screenshots: regenerate all; add `studio-quality-900x800.png` (stacked) and one dark-mode screenshot of Studio
  (`colorScheme: "dark"`).

Planted bugs (run each, confirm a failing test, restore exactly, paste the failing line): set `--c-review` (light) to
`#d49a00`; delete the reduced-motion rule; add `width: 1400px` to `.benchmark-card`; change "no fixtures match" text;
remove one scene fixture from the runbook; make the Studio grid never stack.

## Out of scope
Backend (`src/`) changes, new features, live runs, the manual dry runs (Budi's).

## Verify (the final D4 regression; paste real output)
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
rm -rf web/node_modules && make web-install
make web-types && git diff --exit-code web/src/api/schema.d.ts && git status --porcelain web/src/test/fixtures/  # clean
make web-test && make web-build && find web/dist -type f ! -name '*.map' -size +1M      # nothing
make web-e2e                                                                           # run twice
grep -rn "http://\|https://" web/src --exclude=schema.d.ts | grep -v "src/test/fixtures/"   # nothing
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts)
grep -rn "eslint-disable" web/src web/e2e | grep max-len                                # nothing
make lint && make typecheck && make test                                               # backend 412
git status --porcelain benchmarks/ src/                                                # nothing
```
If `rm -rf web/node_modules` is blocked by the sandbox, run `make web-install` (npm ci) and say so.

## Report back with
Everything AGENTS.md's "Final message" asks for (before: backend 412, Vitest 56, Playwright 24), plus: the output of every
Verify command (both e2e runs); the contrast ratio table (light and dark, every pair, before → after for any token you
changed); the list of `ApiError` callers audited; the 6 planted-bug failing lines; the screenshot files with sizes; and
anything not done, stated plainly at the end.
