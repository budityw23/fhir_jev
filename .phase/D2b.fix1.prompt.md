D2b fix-up round 1. Same rules as before (AGENTS.md and the D2b prompt; Node 20 via
`export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`). Change only what's listed here. No backend changes.

The evaluator reproduced D2b:
- gates green (Vitest 15, Playwright 6 including the guard test, build < 1 MB, backend 408)
- the Studio page logic is right: URL state, overrides sent only when changed, a 250 ms debounce, a redirect for unknown
  modules
- the e2e specs 2, 3, 4 and 6 do what the contract describes
Four blocking problems and two small ones remain.

## 1. The decision lane and its reason are never shown (❌)
`CompareResponse.lane` and `lane_reason` aren't rendered anywhere; the only use is `data.lane === "flagged"` for the
Dinkes card. The lane reasons ("NIK gate failed: P(valid) 0.08", "confidence 0.92 < floor 0.99", "score 80 < threshold 85")
are the heart of the demo, and the D2b checklist item "Colour never the sole signal: DecisionCard lanes render icon +
text" can't pass without them.
- Add a `LaneChip` (e.g. `components/studio/LaneChip.tsx`) rendered at the top of every decision card:
  - an icon + the lane name + colour: `auto_accepted` ✓, `routed` ✓, `flagged` ⚑, `review` ⚠
  - the exact `lane_reason` string next to it
  - `data-testid="lane"` and `data-testid="lane-reason"`
- Vitest: for each of the 3 recorded samples, the chip shows the sample's lane with its icon AND its exact
  `lane_reason`.
- Extend e2e spec 2: after moving the threshold to 85, the lane reason reads `score 80 < threshold 85`.

## 2. VerdictStrip's ground-truth pill is static (❌)
It always renders "Ground truth ✓" and never shows the expectation (UI-S-5; the D2b prompt asked for "the
ground-truth expectation").
- The third pill shows the expected value from `ground_truth`: `expected_action` (quality), `expected_category`
  (router), or `expected_status` (notifiable), e.g. "Ground truth: review_needed".
- Vitest: with the quality sample, the pill shows its `expected_action`; for a router ground truth, its
  `expected_category`.

## 3. Readable formatting, with an ESLint rule that actually works on JSX (❌)
Many JSX lines are 200–576 chars (e.g. DecisionCard.tsx line 24 is 576 chars; ArtifactTabs, ProbabilityBars,
ThresholdSliders, DinkesCard, VerdictStrip, Overview components). ESLint didn't catch them because `max-len` has
`ignoreStrings: true`, which skips EVERY line containing a string literal, and nearly every JSX line has one.
- In `web/eslint.config.js`, remove `ignoreStrings` and `ignoreTemplateLiterals` from `max-len`. Keep `ignoreUrls`,
  `ignoreRegExpLiterals` and the `schema.d.ts` exclusion. If a single genuinely unbreakable string needs it, use an
  `ignorePattern`, not a blanket ignore.
- Reformat every hand-written `.ts` / `.tsx` / config file under `web/` to multi-line JSX with lines ≤ 100 chars.
  This is formatting only: no behaviour change.
- Done means: `npm run lint` passes AND
  `awk 'length > 100' <every hand-written web .ts/.tsx/.js file except schema.d.ts>` prints nothing.

## 4. The required tests are missing (❌)
The D2b prompt required these Vitest tests. The evaluator planted each bug below, and NO test failed. Add tests so
that each mutation makes at least one test FAIL:

| Behaviour | Planted bug that must fail a test |
| --- | --- |
| DinkesCard only when `lane === "flagged"` | remove the `data.lane === "flagged" &&` guard in DecisionCard |
| LevelDistribution hidden in mock, shown in live | make it always render (`true ?` in place of the `jev_client === "live"` check) |
| ThresholdSliders shows only the module's sliders | render the router slider for every module |
| FixturePicker grouping by source, search, "draft" marker | change the "draft" text, or break the grouping / search |
| QuestionBox / questionsFor shows the exact constants | give router the NOTIFIABLE_STATEMENT instead of ROUTE_QUESTION |
| Studio debounce: ONE compare after several quick slider changes (fake timers) | change the 250 ms debounce to 0 |

Run each mutation yourself, confirm the new test fails, then restore the file exactly.

## 5. Small items
- Playwright titles verbatim from Step 11 (e.g. `2. Studio quality: pick \`complete_patient\`, see \`auto_accept\`, drag
  the threshold to 85, see \`review_needed\`.`), and the same for 3, 4 and 6.
- `web/tsconfig.tsbuildinfo` is a TypeScript build cache that was committed by mistake in D2a. Add
  `web/*.tsbuildinfo` to `.gitignore` (allowed in this fix-up only). Don't run git commands; the evaluator untracks it.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)   # nothing
make lint && make typecheck && make test     # backend 408
```
Report back with the changed files, Vitest before (15) → after, the Playwright count, and, for each of the 6 mutations in
item 4, the Vitest summary line showing a failure under it.
