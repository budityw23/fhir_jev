Implement Phase D2b — Overview and Studio, from docs/Jev × FHIR — Demo Technical Implementation Plan.md.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2a built the web foundations you extend (API client and
hooks, types, tokens, `noulView`, shell, the Playwright auto network guard, Makefile `web-*` targets). Keep its lessons:
- never obfuscate or reshape data to satisfy a check
- every test must fail when the behaviour it names is removed (the evaluator plants bugs to check this)
- readable code with lines ≤ 100 chars (ESLint enforces it)

Read before you start:
- the plan: "## Phase D2" → "How D2 Is Organised" (incl. Clarifications); "D2 Contract": Steps 7 and 8 (Overview, Studio +
  the component props table) and Step 11 (tests); "#### Phase D2b — Overview and Studio" (scope, tests, deferred, checklist)
- docs/Jev × FHIR — Demo Plan Requirement.md §3.3 (UI-G-6 colours), §3.4 (UI-O-1…3), §3.5 (UI-S-1…7) for wording/behaviour

The contract is the source of truth. If something can't work as written, stop and explain; don't redesign it.

## Environment
- Node 20 for all `web/` work: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`.
- `~/.npm` and `~/.cache/ms-playwright` are writable. No new dependencies are needed: everything is in D2a's lockfile.
- No backend changes in D2b.

## Scope (D2b only). Everything below lives in `web/src`.

### Overview (Step 7, UI-O-1…3): replace the placeholder
- `components/overview/ArchitectureDiagram.tsx`: inline SVG with FHIR JSON → Serializer → Jev (Choice / Score / Noul) →
  Decision → Action; CSS dash animation on the edges; a dimmed "LLM reasoning layer · next" branch; no animation under
  `prefers-reduced-motion: reduce`.
- `components/overview/ModuleCard.tsx` ×3: Quality (Score), Router (Choice), Notifiable (Noul).
  - Data: `GET /api/v1/demo/benchmarks` → take the FIRST (newest) summary → `GET /api/v1/demo/benchmarks/{name}` →
    `modules[<key>]`, where the key is `quality_scorer` / `bundle_router` / `notifiable_detector`.
  - Show `jev_accuracy` as a percentage and `latency.p95_ms`, plus the report's `mode` and `dataset`.
  - No reports → the text "no report yet". An "Open in Studio" link → `/studio/<module>`.
- A one-line problem statement and a "Start demo" button → `/studio/quality`.

### Studio (Step 8, UI-S-1…7): replace the placeholder
Implement every component in `components/studio/` with EXACTLY the props in the Step 8 table:
`FixturePicker`, `JsonView`, `FlatStateTable`, `QuestionBox`, `DecisionCard` (switching to `QualityDecision` /
`RouterDecision` / `NotifiableDecision`), `ScoreGauge`, `LevelDistribution`, `ProbabilityBars`, `NoulMeter`, `DinkesCard`,
`ThresholdSliders`, `VerdictStrip`, `ArtifactTabs`, `LatencyLine`.

Data mapping, where the contract leaves it implicit (field names are from `CompareResponse`):
- **Page:** `pages/Studio.tsx` at `/studio/:module`, with the module in {quality, router, notifiable}; any other value →
  redirect to `/studio/quality`. Three columns at ≥ 1024 px, stacked below.
- **URL state:** the fixture is `?fixture=<id>`. Picking a fixture updates the URL, and reloading restores it.
- **Resource:** `useFixture(id)`. The compare input is `{ resource, fixture_id: id, thresholds }`, sent through `useCompare`.
- **Thresholds:** local state initialised from `useDemoConfig().thresholds`, with a "Reset" that restores those defaults.
  Only changes the user makes are sent, as `ThresholdOverrides`. Debounce 250 ms before re-running the compare
  (`lib/debounce.ts`).
- **FixturePicker:** `useFixtures({ module })`; grouped by `source`; a search box filtering by `name` / `label`; each item
  shows `label`, a "hard" tag when `difficulty === "hard"`, and a "draft" marker when `approved === false`.
- **JsonView:** the raw fixture, collapsible (`@uiw/react-json-view`).
- **FlatStateTable:** `serialized_state`; booleans as ✓ / ✗ chips (with text), `null` rows amber.
- **QuestionBox:** the exact strings from `DemoConfig.questions`: quality → `QUALITY_SCORE_QUESTION` and
  `NIK_VALIDATION_STATEMENT`; router → `ROUTE_QUESTION`; notifiable → `NOTIFIABLE_STATEMENT`.
- **QualityDecision:**
  - `ScoreGauge` (score, threshold tick at `thresholds.quality_threshold`, confidence)
  - `level`, `action`, `missing_fields` chips
  - NIK gate from `nik_valid` / `nik_confidence`, rendered with `noulView(nik_confidence)`
  - `LevelDistribution`: `jev_raw[0].result.level_probabilities`, shown ONLY in live mode (`useHealth().jev_client === "live"`)
- **RouterDecision → ProbabilityBars:**
  - `probabilities` = `jev.probabilities` (all 5 categories)
  - `winner` = the model's choice `jev_raw[0].result.choice`
  - `floor` = `thresholds.route_confidence_minimum`, drawn as a dashed line
  - `overridden` = `override_applied`
  - when overridden, the note reads exactly `overridden: confidence {jev.confidence:.2f} < {floor:.2f}`
    (e.g. "overridden: confidence 0.92 < 0.99")
- **NotifiableDecision:**
  - a large yes/no from `noulView(jev.probability)`, plus the `status`
  - `NoulMeter` with `pTrue = jev.probability`, `reviewBand = [thresholds.notifiable_review, thresholds.notifiable_confirmed]`,
    and the not / review / confirmed bands shaded
  - `DinkesCard` only when `lane === "flagged"`. Urgency isn't exposed by any API, so show the plan's fallback text:
    "Report to Dinkes · mandatory reporting". Don't add a backend endpoint.
- **ThresholdSliders:** only the module's sliders:
  - quality → `quality_threshold`, 0–100, step 1
  - router → `route_confidence_minimum`, 0–1, step 0.01
  - notifiable → `notifiable_confirmed` and `notifiable_review`, each 0–1, step 0.01; the UI keeps review ≤ confirmed
  Each is a labelled `<input type="range">`, so it's accessible and testable.
- **VerdictStrip:** three pills, Jev · Rules · Ground truth, each ✓ / ✗ from `verdict` (showing `jev_decision`,
  `rule.decision` and the ground-truth expectation); rendered only when `ground_truth` is not null.
- **ArtifactTabs:** Response (the whole `CompareResponse` JSON), Flag (only when `jev.flag_resource`), AuditEvent
  (`audit_event`); each has a "copy" button.
- **LatencyLine:** Jev ms = the sum of `jev_raw[*].result.latency_ms`, labelled "simulated" in mock mode; end-to-end ms =
  `X-Request-Duration-Ms` of the compare response, taken from `subscribeLastRequest`.
- **Lane and decision chips** always pair colour with an icon and text (UI-G-6): accept ✓, review ⚠, flag ⚑, neutral ○.
- **Changing the fixture or a threshold re-runs `useCompare`**; `placeholderData` keeps the previous card visible;
  CSS transitions only.
- **Errors:** any `ApiError` renders the D2a `ErrorCard`.

## Tests
- Vitest, contract (verbatim): "`VerdictStrip` hides without ground truth.", "`ProbabilityBars` shows the override note.",
  "`DecisionCard` renders all three modules from **recorded responses** in
  `web/src/test/fixtures/compare_{quality,router,notifiable}.json`."
- Vitest, additional:
  - ThresholdSliders shows only the module's sliders
  - LevelDistribution is hidden in mock mode and shown in live mode
  - DinkesCard only for `lane === "flagged"`
  - FixturePicker grouping, search, and the "draft" marker
  - QuestionBox shows the exact constants
  - the Studio debounce sends ONE compare after several quick slider changes (fake timers)
- Playwright, verbatim from Step 11 (the D2a auto network guard stays active):
  - "2. Studio quality: pick `complete_patient`, see `auto_accept`, drag the threshold to 85, see `review_needed`."
  - "3. Studio router: `mixed_bundle`, floor 0.99, see the override note."
  - "4. Studio notifiable: the JE fixture shows the Flag tab and the Dinkes card; common cold shows neither."
  - "6. A deep link reload of `/demo/studio/router?fixture=…` works."
- Spec 1 must keep passing, now against the real Overview.

## Out of scope (D2c or later)
The Playground page (keep its placeholder), e2e spec 5, the screenshots, and the D3 / D4 pages.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e          # Vitest all pass; Playwright specs 1, 2, 3, 4, 6 (+ guard test)
find web/dist -type f ! -name '*.map' -size +1M          # nothing
grep -rn "http://\|https://" web/src --exclude=schema.d.ts | grep -v "src/test/fixtures/"   # nothing
make lint && make typecheck && make test                 # backend still 408
```
Plan a manual smoke too: `make demo`, open /demo and /demo/studio/quality in the Playwright browser, and describe what
renders.

## Report back with
Everything AGENTS.md's "Final message" asks for (backend 408; web before: Vitest 12, Playwright 2), plus the web test
counts and summary lines, the Verify outputs, and the list of Studio component files with their exported props types.
