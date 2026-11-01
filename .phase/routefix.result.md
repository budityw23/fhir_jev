Implemented the experiment exactly, with mock Jev only.

Changed files:

- [serializer/bundle.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/serializer/bundle.py): added `contains_encounter` directly after `contains_medication`.
- [modules/bundle_router.py](/home/budi/code/sphere_project/FHIR_JEV/src/jev_fhir/modules/bundle_router.py): replaced the question; options unchanged.
- [test_serializer.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_serializer.py): added membership, Condition-dominance, and reference-only tests.
- [test_decision_modules.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_decision_modules.py): added exact stub-call checks and baseline invariance across all 102 Bundle fixtures.
- Generated [compare_router.json](/home/budi/code/sphere_project/FHIR_JEV/web/src/test/fixtures/compare_router.json): new question and field; simulated token count changed from 40 to 33. This was the only file changed by `make web-types`.

No existing test assertions were altered. No fallback expectation adjustments were needed. No added helpers beyond test call recording, implementation deviations, or benchmark reports.

Verification:

```text
make lint: passed
make typecheck: Success: no issues found in 62 source files
===================== 563 passed, 1015 warnings in 14.22s ======================
TOTAL                                          1399     22    98%
```

Test count: **456 → 563**. Coverage for both changed source files:

```text
src/jev_fhir/modules/bundle_router.py            26      0   100%
src/jev_fhir/serializer/bundle.py                32      0   100%
```

Frontend lint and typecheck passed with the requested Node PATH:

```text
Tests  60 passed (60)
Duration  3.77s
29 passed (44.6s)
```

Real curl POST to `/api/v1/demo/compare/router`, using `encounter_bundle.json`, returned HTTP 200. Relevant response fields:

```json
"jev_raw":[{"primitive":"choice","question":"Which processing pipeline should handle this FHIR Bundle?","options":["lab_result","encounter_summary","immunization_report","medication_dispense","unknown"],"result":{"choice":"encounter_summary","confidence":0.92,"probabilities":{"lab_result":0.02,"encounter_summary":0.92,"immunization_report":0.02,"medication_dispense":0.02,"unknown":0.02},"latency_ms":21.0,"tokens_used":14}}]
```

```json
"serialized_state":{"resource_type":"Bundle","bundle_type":"collection","entry_count":2,"entry_resource_types":["Encounter","Condition"],"dominant_resource_type":"Encounter","has_patient_reference":true,"has_encounter_reference":true,"contains_lab_codes":false,"contains_condition_codes":true,"contains_immunization":false,"contains_medication":false,"contains_encounter":true}
```

Planted-bug results, in order a–c:

```text
FAILED tests/test_serializer.py::test_bundle_contains_encounter_tracks_entries[True]
FAILED tests/test_serializer.py::test_bundle_contains_encounter_when_conditions_dominate
FAILED tests/test_decision_modules.py::test_bundle_router_sends_pipeline_question_and_encounter_state
```

Each mutation exited 1. Backup/restored SHA-1 output matched:

```text
3e193c91279a73d535460b25d149aa6cc7c28e54  /tmp/routing-mutations-ql5atdh4/a.py
3e193c91279a73d535460b25d149aa6cc7c28e54  src/jev_fhir/serializer/bundle.py

3e193c91279a73d535460b25d149aa6cc7c28e54  /tmp/routing-mutations-ql5atdh4/b.py
3e193c91279a73d535460b25d149aa6cc7c28e54  src/jev_fhir/serializer/bundle.py

abb98e00d775c3f26c6efe4b35e4939188bd0de7  /tmp/routing-mutations-ql5atdh4/c.py
abb98e00d775c3f26c6efe4b35e4939188bd0de7  src/jev_fhir/modules/bundle_router.py
```

After restoration: `3 passed, 4 warnings in 0.37s`. Temporary backups were deleted.

Final `git status --porcelain`:

```text
 M "docs/Jev \303\227 FHIR \342\200\224 Article Draft.md"
 M "docs/Jev \303\227 FHIR \342\200\224 LinkedIn Post Draft.md"
 M src/jev_fhir/modules/bundle_router.py
 M src/jev_fhir/serializer/bundle.py
 M tests/test_decision_modules.py
 M tests/test_serializer.py
 M web/src/test/fixtures/compare_router.json
?? .phase/routefix.prompt.md
?? "docs/Jev \303\227 FHIR \342\200\224 LinkedIn PASTE.html"
```

The docs changes and untracked files predated this work and were untouched. `git diff --check` passed. No uvicorn process or listener on ports 18772/8010 remains. Nothing committed.

Open questions for the evaluator: none.