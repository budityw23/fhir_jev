Implement Phase D2c — Playground, screenshots, and final D2 regression, from
docs/Jev × FHIR — Demo Technical Implementation Plan.md. This is the last D2 sub-phase.

Follow AGENTS.md (standing rules). Read .phase/progress.md first: D2a (foundations) and D2b (Overview and Studio, including
`LaneChip`, `DecisionCard`, `ArtifactTabs`, `LatencyLine`, `ErrorCard`) are done; reuse those components. Keep the lessons:
- never obfuscate data to pass a check
- every test must fail when the behaviour it names is removed (the evaluator plants bugs)
- lines ≤ 100 chars; ESLint `max-len` must keep covering JSX, so don't re-add `ignoreStrings`
- render the backend's explanation fields (`lane`, `lane_reason`)

Read before you start:
- the plan: "## Phase D2" → "How D2 Is Organised" (incl. Clarifications); "D2 Contract": Step 9 (Playground) and Step 11
  (tests, screenshots); "#### Phase D2c": scope, tests, and the **Final D2 checklist**
- docs/Jev × FHIR — Demo Plan Requirement.md §3.9 (UI-PL-1…3)

The contract is the source of truth. If something can't work as written, stop and explain.

## Environment
Node 20 for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. No new dependencies. No backend changes.

## Scope (D2c only)

### Playground page (Step 9, UI-PL-1…3): replace the placeholder at `/playground` (`web/src/pages/Playground.tsx`)
- **Module selector:** quality / router / notifiable.
- **Editor:** `@uiw/react-codemirror` with `@codemirror/lang-json`.
  - JSON checking with `JSON.parse` (don't import `@codemirror/lint`; it isn't a direct dependency).
  - When the text isn't valid JSON, show the parse error inline and disable **Run**.
- **"Load fixture as starting point":** pick a fixture for the selected module (reuse `FixturePicker` or `useFixtures`),
  and load its JSON into the editor pretty-printed (2 spaces). The user can then edit it freely.
- **Run:** `POST /api/v1/demo/compare/{module}` with `{ resource }` (quality also sends `resource_type` from
  `resource.resourceType`). **Never send `fixture_id`**, even when the text came from a loaded fixture: the Playground is
  free-form input with no ground truth.
- **Result:** the same `DecisionCard` (with its `LaneChip`), `ArtifactTabs` and `LatencyLine` as the Studio, and **no
  `VerdictStrip`** (UI-PL-3).
- **Errors:** any `ApiError` (e.g. a 422 for FHIR-invalid input) renders the D2a `ErrorCard`, showing `error`, `detail`
  and `request_id`.

### Screenshots (Step 11)
Add a Playwright spec (e.g. `e2e/screenshots.spec.ts`) that captures full-page screenshots into `web/e2e/screenshots/`
(git-ignored) at **1280×720 and 1920×1080** for each page:
- Overview
- Studio quality with `complete_patient`
- Studio router with `mixed_bundle` at floor 0.99
- Studio notifiable with `japanese_encephalitis_a83`
- Playground after a successful Run
Wait for each page's decision content before capturing. Name the files `<page>-<width>x<height>.png`. The auto network
guard stays active.

## Tests
- Playwright (verbatim from Step 11): "5. Playground: an invalid Condition shows the ErrorCard with a request id."
  - Use JSON that is VALID JSON but INVALID FHIR, e.g. a `Condition` whose `code` is a number, or a `Condition` without
    the required `subject`, so it reaches the backend and returns a 422.
  - Assert the ErrorCard shows a `request_id` that is non-empty and matches a UUID pattern.
- Vitest, contract (D2c section): the Playground never sends `fixture_id` (capture the POST body with a mocked `fetch`),
  including after loading a fixture as the starting point.
- Vitest, additional:
  - invalid JSON disables Run and shows the parse error
  - loading a fixture fills the editor with pretty-printed JSON
  - a successful Run renders DecisionCard and LaneChip, and NO VerdictStrip
  - a 422 renders ErrorCard with the request id
- The evaluator will plant bugs such as "send fixture_id", "render VerdictStrip", "enable Run on invalid JSON" and
  "swallow the ApiError"; each must make a test fail.

## Out of scope
The D3 Pipeline and D4 Benchmarks pages (keep their placeholders), presenter mode, and any backend change.

## Final D2 regression (do this last and paste the evidence)
Run the plan's **Final D2 checklist** (the original 14 items + "Final code matches the full D2 contract"), from a clean
`rm -rf web/node_modules`:
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
rm -rf web/node_modules && make web-install
make web-test && make web-types && git diff --exit-code web/src/api/schema.d.ts
make web-build && find web/dist -type f ! -name '*.map' -size +1M               # nothing
make web-e2e                                                                    # specs 1–6 + guard + screenshots
ls -la web/e2e/screenshots/
grep -rn "http://\|https://" web/src --exclude=schema.d.ts | grep -v "src/test/fixtures/"   # nothing
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)   # nothing
make lint && make typecheck && make test                                        # backend 408
make demo &   # then:
curl -s localhost:8000/demo | grep -c '<div id="root">'; curl -s localhost:8000/demo/studio/quality | grep -c '<div id="root">'
# stop it by the PID listening on 8000 (make spawns uvicorn as a child)
```

## Report back with
Everything AGENTS.md's "Final message" asks for (backend 408; web before: Vitest 22, Playwright 6), plus the output of
every Final D2 checklist command above, and the list of screenshot files with sizes.
