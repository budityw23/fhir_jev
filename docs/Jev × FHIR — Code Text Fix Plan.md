# Jev × FHIR — Plan: Send Condition `code.text` to Jev

Nov 1, 2026 · @budi · Status: **implemented, not committed; live re-run done**

Result (`bench_20261101T001036Z`): notifiable accuracy 0.839 → 0.935 and recall 0.737 → 0.895. Exactly
three notifiable rows flipped, all three text-only fixtures, and all three are now correct. The two
remaining misses, `hiv_b20` and `typhoid_subcode_a01_0`, went to `review_needed`. Quality (0.676 → 0.648)
flipped two rows the fix doesn't touch, so that's run-to-run noise.

Steps 2–4 passed. Two e2e tests that assumed the newest report was mock were also fixed: they now select
the committed mock report by name, so future live reports won't break them.

## Problem

`ConditionSerializer` reads `code.coding` but never reads `code.text`. A Condition that names its
disease only in free text reaches Jev with `code_value`, `code_display` and `code_system` all null, so
the model is asked to judge a condition it can't see.

The notifiable benchmark therefore understates what the model can do. In live report
`bench_20261031T150439Z`, Jev missed 5 of 19 notifiable cases (recall 0.737). Three of those five are
text-only fixtures:

| Fixture | `code.text` | Jev confidence |
| --- | --- | --- |
| `benchmarks/dataset/hard/conditions/dbd_text_only.json` | Demam berdarah dengue (DBD) | 0.47 |
| `benchmarks/dataset/hard/conditions/tb_paru_text_only.json` | TB paru | 0.50 |
| `benchmarks/dataset/demo/conditions/condition_dbd_text_only.json` | Demam berdarah dengue (DBD) | 0.49 |

The other two misses (`hiv_b20`, `typhoid_subcode_a01_0`) have codes and aren't affected by this bug.

## Goal

Jev receives `code.text` for every Condition, and the benchmark measures it fairly.

**Success is not a particular recall number.** The fix is done when the text reaches the model and the
result is recorded, whatever it turns out to be. Don't change labels, thresholds or prompts to improve it.

## Changes

| # | File | Change |
| --- | --- | --- |
| 1 | `src/jev_fhir/serializer/condition.py` | Add `code_text` to the flat state: the string in `code.text`, truncated to 200 characters, or `None` |
| 2 | `src/jev_fhir/modules/notifiable_detector.py:74` and `:94` | Use `code_display or code_text or "Unknown condition"` for `condition_display` |
| 3 | `tests/test_serializer.py:91` | Add `"code_text": None` to the exact-match dict (the new field is the reason, not a weakened test) |
| 4 | `web/src/test/fixtures/compare_notifiable.json` | Regenerate with `make web-types` |

The 200-character limit keeps a long note from inflating token use and reduces how much free text
leaves the system. It's a judgment call, see Decisions.

**Must stay unchanged:** `src/jev_fhir/baselines/notifiable.py` (the rule baseline stays code-only),
`MockJevClient`'s decision logic, all labels and fixtures, `tests/test_api.py`, and the Phase 4 response
models.

## Effect on the mock

`MockJevClient` decides notifiable cases from `code_value` alone, so its decisions don't change and it
keeps missing text-only cases. That's deliberate: teaching it to read text would make mock evidence look
like model evidence.

It does hash the whole state for simulated latency and token counts, so those values will change for
Conditions. Any test that asserts them needs to be found and reviewed.

## Tests to add

1. A Condition with only `code.text` serializes with `code_text` set and the coded fields null.
2. A Condition with both coding and text keeps both.
3. A Condition with no `code` gives `code_text: None`.
4. Text over 200 characters is truncated to exactly 200.
5. A non-string `code.text` is rejected by `Condition.parse_obj`, or gives `None`.
6. With a stubbed Jev client, the state passed to `noul` contains the text.
7. A confirmed text-only Condition produces a Flag with the text as its display, not
   "Unknown condition", and its `condition_code` stays `unknown`.
8. Mock decisions are unchanged for every Condition fixture, compared with the rule that the mock
   reads only `code_value`.

## Rollout

| Step | Who | Done when |
| --- | --- | --- |
| 1. Commit or stash the current uncommitted `web/src` work | Budi | `git status` no longer shows it mixed in with this fix |
| 2. Implement changes 1–4 and the tests | Codex, mock only | `make lint typecheck test` pass; coverage TOTAL ≥ 95%, touched files ≥ 90% |
| 3. Check the frontend | Codex | `npm run lint`, `typecheck`, `test` and `e2e` pass in `web/` |
| 4. Evaluate | Claude | Real uvicorn check: the Studio state for `dbd_text_only` shows `code_text`; planted bug makes a test fail |
| 5. Live re-run | **Budi** | `make bench-live-full` writes a new report |
| 6. Compare reports | Claude | Row-by-row diff of old and new notifiable results, not only the totals |
| 7. Update content | Claude + Codex | See below |

Step 5 is manual because automated runs must never call the live API. A full run cost about $0.006.

The live model may vary between runs, and the new field changes every Condition's state, even when it's
null. So step 6 should report which rows changed, and treat a change on a coded fixture as possible noise
rather than a result of this fix.

## Content to update after the re-run

- `docs/Jev × FHIR — Article Draft.md`
- `docs/Jev × FHIR — LinkedIn Article Draft.md`
- `docs/Jev × FHIR — LinkedIn Post Draft.md`
- `docs/demo-runbook.md`: scene 3 talk track, and `web/src/scenes.ts` if the scene's point changes
- `docs/demo-video/jev-fhir-demo.webm`: re-record, because the Benchmarks scene shows the old report

**Video caption 10** ("The live model misses this one too.") may become false. The video's Studio scenes
run on the mock, which will still miss this case, so rewrite the caption to match the new live result.

## Decisions for Budi

1. **Is 200 characters right?** `code.text` is normally a short label, but in real data it could contain
   notes or identifying details. Recommendation: keep 200 for now.
2. **Should the UI show `code_text` under "What Jev sees"?** It should appear automatically, since the
   panel renders the serialized state. Step 4 confirms that.
3. **Should a text-only confirmed case create a Flag at all?** Today it would create one with code
   `unknown`. Recommendation: keep it, because a person confirms the report, and the display text makes
   it readable. The alternative is sending these cases to review.

## Out of scope

Related gaps worth separate fixes:

- `ObservationSerializer` drops `code.text` the same way. Observations go through quality scoring, so the
  effect is different.
- Serializers read only the first `coding`, so a second coding such as ICD-10 after SNOMED is invisible.
- The rule baseline's exact ICD-10 match and its lack of a `verificationStatus` check. Improving it would
  be a fairer comparison, but it's a separate change, because mixing it in would hide this fix's effect.
- Label approval, still pending for 124 labels.
