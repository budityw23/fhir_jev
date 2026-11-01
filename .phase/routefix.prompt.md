Implement a small routing experiment. Follow AGENTS.md (standing rules). Read `.phase/progress.md` first.
Finish the whole task before you stop, including the planted bugs.

## Why

In the live benchmark, Jev got 0 of 11 encounter Bundles right when they held 3 or more Conditions, and sent
all 7 misrouted mixed Bundles to their most common resource type. Two likely causes: `ROUTE_QUESTION` asks
what a Bundle "primarily" contains, and the flat state has `contains_lab_codes`, `contains_immunization` and
`contains_medication` but nothing direct for encounters. This change tests those causes. It's an experiment:
don't tune anything to improve a result.

## Scope (these files only)

1. `src/jev_fhir/serializer/bundle.py`: add `"contains_encounter": "Encounter" in resource_types` directly
   after `contains_medication`.
2. `src/jev_fhir/modules/bundle_router.py`: set `ROUTE_QUESTION` to exactly:
   `"Which processing pipeline should handle this FHIR Bundle?"`
   Don't change `ROUTE_OPTIONS`.
3. `tests/test_serializer.py` and `tests/test_decision_modules.py`: update exact-match expectations for the
   new field and question, and add the tests below.
4. Generated files that `make web-types` really changes because of these edits, such as
   `web/src/test/fixtures/compare_router.json`. Report each one.

Only if a test fails because `MockJevClient`'s hash-based fallback changed a simulated value: update that
test's expected value and name it in your report. The mock hashes the state and question, so simulated
latency, tokens and fallback choices for Bundles can shift. Don't change the mock.

## Must not change

`src/jev_fhir/baselines/`, `src/jev_fhir/jev_client/mock.py`, all labels and fixtures, `tests/test_api.py`,
`tests/snapshots/`, the Phase 4 response models, `pyproject.toml`, `.env*`, `web/video/`, `web/src/pages/`,
`web/src/components/`, everything in `docs/` and `benchmarks/results/`. Don't use `git checkout`, `git restore`,
`git stash`, `git reset` or `git clean`. Don't commit.

**Mock Jev only.** Never run `make bench-live*` or `make smoke-live`, and never read `.env`. Delete by exact
name any `benchmarks/results/bench_*` file your verification creates; never delete an existing one.

## Tests to add

1. A Bundle with an Encounter entry gives `contains_encounter: True`, and without one gives `False`.
2. A Bundle holding one Encounter and eight Conditions has `contains_encounter: True` while
   `dominant_resource_type` stays `Condition`.
3. An Encounter that's only referenced, with no Encounter entry, gives `contains_encounter: False` and
   `has_encounter_reference: True`.
4. With a stubbed client, `choice` receives the exact new question and the state contains
   `contains_encounter`.
5. The rule baseline's result is unchanged across every Bundle fixture when `contains_encounter` is removed
   from the state, which shows the rules don't use the new field.

## Verify (real output)

1. `make lint && make typecheck && make test`. Baseline: 456 tests, TOTAL 98%. Required: TOTAL ≥ 95%, each
   touched module ≥ 90%. Paste the summary line.
2. In `web/`, with `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`: `npm run lint`,
   `npm run typecheck`, `npm run test`, `npm run e2e`. Expected: 60 and 29 passing.
3. Real server on port 18772, then stop it:
   `DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18772`
   POST an encounter Bundle fixture to the demo compare endpoint with body `{"resource": <the Bundle>}`. Paste
   the real output showing `serialized_state.contains_encounter` and the question in `jev_raw`.
4. **Planted bugs, run them yourself.** Copy the file aside, plant, run the matching test, paste the FAILED
   line, restore, and show matching `sha1sum` values.
   a. `contains_encounter` always returns `False`.
   b. Check `dominant_resource_type == "Encounter"` instead of membership.
   c. Restore the old `ROUTE_QUESTION`.
5. `git status --porcelain`, and confirm no server is left running.

## Report back

Everything AGENTS.md's Final message asks for (test count before: 456), the planted-bug output, every generated
file that changed, and every existing assertion you altered, and why.
