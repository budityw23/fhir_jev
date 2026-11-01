---
title: "I Built a Jev Decision Layer Over FHIR, and Its Worst Failures Were in My Own Pipeline"
published: false
tags: fhir, healthcare, ai, python
---

A FHIR resource can pass validation and still be the wrong thing to act on. I built a small decision layer for that gap: it takes parsed FHIR R4 resources, sends a flattened state to TypeSafe AI's Jev model, and turns the answer into accept, route, flag or human review.

On 204 synthetic records, the first live run lost routing to my hand-written rules, 0.814 to 0.922, and missed too many notifiable diseases. Both failures came from my own setup. One was a serializer bug and the other was a badly framed routing question. After fixing both, Jev scored above the rules on all three decisions, on the same records. It still misses my latency target by a wide margin.

This is a proof of concept. It runs on synthetic data and it is not connected to any production system.

## What validation does not answer

Here is part of a Patient that parses as FHIR R4:

```json
{
  "resourceType": "Patient",
  "id": "invalid-nik",
  "identifier": [{"system": "nik", "value": "317301010190000"}],
  "name": [{"family": "Wijaya"}]
}
```

The NIK is Indonesia's national ID, and it has 16 digits. This one has 15. A Condition can have the same problem in a different form: well-formed, coded as dengue, with `verificationStatus` set to `refuted`. The patient does not have dengue, and the resource is still structurally correct.

Conformance checking answers one question: does this resource meet the spec? A pipeline has to answer a different one: what should happen to this resource now?

| | Conformance | Decision layer |
| --- | --- | --- |
| Question | Does it meet the spec? | What do we do with it? |
| Output | Pass or fail, with issues | An action and a confidence |
| Defined by | Spec and profiles | Workflow and risk tolerance |
| When unsure | Does not apply | Sends it to a person |

Profiles can cover more of this than people expect. A FHIRPath invariant could enforce a 16-digit NIK, so that example does not need a model. The boundary I care about is not rules versus AI. It is *is this correct?* versus *what happens next?*

## The pipeline

Jev is a decision model. It takes a structured state and a fixed question, and returns a typed answer with a confidence. It does not generate text. The project uses its three primitives: **Choice** picks one option from a list, **Score** returns a number on a scale, and **Noul** answers a statement with a probability that it is true.

![Pipeline: FHIR JSON, parse, flatten, Jev, threshold, then one of four lanes](dev-to-images/pipeline.png)

The service is FastAPI with Pydantic v2, and it makes three decisions:

| Decision | Primitive | Output |
| --- | --- | --- |
| Is this resource good enough to accept automatically? | Score, plus Noul for the NIK | Score 0 to 100, then accept or review |
| Which pipeline should get this Bundle? | Choice | One of five fixed categories |
| Must this Condition be reported? | Noul | Probability, plus a Flag when confirmed |

## Conformance runs first, then the state gets small

Every serializer parses the resource before it extracts anything. A resource that fails parsing raises an error, so no Jev call happens. This is lighter than full profile and terminology validation, but the order is the design: conformance first, decisions on top.

```python
# src/jev_fhir/serializer/patient.py
def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
    """Validate a Patient and produce a missing-field-safe flat state."""
    Patient.parse_obj(resource)

    identifier = first_mapping(resource.get("identifier"))
    identifier_value = identifier.get("value") if identifier is not None else None

    return {
        "resource_type": self.resource_type(),
        "has_identifier": identifier is not None,
        "identifier_value_length": len(identifier_value)
        if isinstance(identifier_value, str)
        else None,
        # remaining demographic fields omitted
    }
```

The model never receives the NIK itself, only its length. This is the state produced from the full version of that Patient:

```json
{
  "resource_type": "Patient",
  "has_identifier": true,
  "identifier_system": "nik",
  "identifier_value_length": 15,
  "has_name": true,
  "name_family": "Wijaya",
  "has_birth_date": true,
  "has_gender": true,
  "has_address": true,
  "address_country": "ID",
  "has_telecom": false,
  "telecom_count": 0,
  "field_completeness": 8,
  "field_total": 10
}
```

A small state keeps each call cheap and easy to inspect. The demo UI shows this exact state next to every decision, which made debugging much easier later. It is not a privacy solution, though. `name_family` is still in there, and real data would need a proper review.

## A probability is not an action

Thresholds turn a model output into something the pipeline can do. The router has a confidence floor, and anything below it becomes `unknown`:

```python
# src/jev_fhir/modules/bundle_router.py
state = self._serializer.serialize(bundle)
result = await self._jev_client.choice(state, ROUTE_QUESTION, ROUTE_OPTIONS)
category = result.choice if result.confidence >= confidence_minimum else "unknown"
```

The quality scorer treats the NIK as a gate. A high completeness score cannot override it:

```python
# src/jev_fhir/modules/quality_scorer.py
passes_nik_gate = nik_valid is not False
action = (
    "auto_accept"
    if score_result.score >= threshold and passes_nik_gate
    else "review_needed"
)
```

Notifiable detection uses two thresholds, which gives it a band for human review:

![Notifiable bands: below 0.5 not notifiable, 0.5 to 0.8 review, 0.8 and above confirmed](dev-to-images/notifiable-bands.png)

```python
# src/jev_fhir/modules/notifiable_detector.py
if result.probability >= confirmed_threshold and result.answer:
    status = "confirmed_notifiable"
    is_notifiable = True
    # builds the FHIR Flag here
elif result.probability >= review_threshold:
    status = "review_needed"
    is_notifiable = False
    flag_resource = None
else:
    status = "not_notifiable"
    is_notifiable = False
    flag_resource = None
```

The review band is the part conformance has no equivalent for. The system can say it is not sure, and that outcome has a defined place to go.

## How I measured it

I compared Jev with a transparent rule baseline for each decision. The rules are deliberately simple: a field-count score, a length check for the NIK, routing on resource types and LOINC signals, and an exact ICD-10 lookup.

The dataset has 204 labelled fixtures, including a hard set built to separate semantic judgment from exact matching. Labels are never computed from the logic under test. The test suite uses a mock Jev client and never calls the live API, and the benchmark runs against the live model only when I ask it to.

| Decision | Fixtures | Jev, first run | Jev, final | Rules | My target |
| --- | ---: | ---: | ---: | ---: | --- |
| Quality (accuracy) | 71 | 0.676 | **0.662** | 0.549 | ≥ 0.85, missed |
| Routing (accuracy) | 102 | 0.814 | **0.951** | 0.922 | ≥ 0.90, met |
| Notifiable (accuracy) | 31 | 0.839 | **0.935** | 0.677 | none set |
| Notifiable (recall) | 31 | 0.737 | **0.895** | 0.579 | ≥ 0.95, missed |
| Notifiable (precision) | 31 | 1.000 | **1.000** | 0.846 | ≥ 0.80, met |

The rest of this article explains how the first-run column became the final one.

## The bug the state panel exposed

My first live run scored 0.839 on notifiable detection, with a recall of 0.737. The score alone gave no hint of why.

The cause showed up while I was reviewing the demo. The state panel for a text-only dengue case showed `code_value`, `code_display` and `code_system` all null, with no disease name anywhere. My serializer read `code.coding` and never read `code.text`, so the model was judging a blank. Three of the five misses had the disease name only in `code.text`, such as "Demam berdarah dengue (DBD)" and "TB paru".

The fix is small:

```diff
# src/jev_fhir/serializer/condition.py
+CODE_TEXT_MAX_LENGTH = 200

         code = resource.get("code")
+        code_text = code.get("text") if isinstance(code, dict) else None
         onset = resource.get("onsetDateTime")

             "code_display": first_coding_value(code, "display"),
+            "code_text": code_text[:CODE_TEXT_MAX_LENGTH] if isinstance(code_text, str) else None,
             "clinical_status": first_coding_code(resource.get("clinicalStatus")),
```

The 200-character limit keeps a long note from inflating token use and limits how much free text leaves the system. I kept the rule baseline code-only, so the comparison stayed fair. I also kept the mock code-only, because teaching it to read text would make mock results look like model evidence.

I then compared the two live reports row by row. Exactly three notifiable rows changed, and they were the three I expected:

| Fixture | Confidence before | Confidence after | Result |
| --- | ---: | ---: | --- |
| `dbd_text_only` | 0.47 | 0.90 | wrong → correct |
| `tb_paru_text_only` | 0.50 | 0.89 | wrong → correct |
| `condition_dbd_text_only` | 0.49 | 0.89 | wrong → correct |

Accuracy went from 0.839 to 0.935, and recall went from 0.737 to 0.895. The earlier score was measuring my pipeline, not the model. Without the row-level comparison, I could not have told that apart from noise, because quality accuracy moved from 0.676 to 0.648 between the same two runs on rows the fix does not touch.

The two remaining misses, `B20` HIV and typhoid `A01.0`, have proper codes. Both landed in the review band at about 0.77, so a person would see them. All 19 notifiable cases were either confirmed or sent to review, and none was dismissed.

## Why rules first won routing

My first explanation for the routing loss was that routing is mostly clear logic. I had written that down, but I had not measured it. So I compared the flat state of every Bundle Jev got right and wrong.

All 12 of its encounter errors followed one pattern:

| Conditions in the Bundle | Bundles | Jev correct |
| ---: | ---: | ---: |
| 1 | 6 | 6 |
| 2 | 2 | 1 |
| 3 or more | 11 | 0 |

Both live runs showed this, and 100 of the 102 routing decisions were identical across the runs. This was a systematic failure, not noise.

Two things in my setup could explain it. The question was "What type of clinical data does this FHIR Bundle primarily contain?". One Encounter with eight Conditions primarily contains Conditions, and no category exists for that, so `unknown` was a fair answer. The same word would also explain the other errors, because all seven misrouted mixed Bundles went to the pipeline for their most common resource type.

The state was also uneven. It had direct flags for labs, immunizations and medications, which scored at 1.00 confidence, but nothing direct for encounters. `dominant_resource_type` said `Condition`.

I changed both:

```diff
# src/jev_fhir/modules/bundle_router.py
-ROUTE_QUESTION = "What type of clinical data does this FHIR Bundle primarily contain?"
+ROUTE_QUESTION = "Which processing pipeline should handle this FHIR Bundle?"

# src/jev_fhir/serializer/bundle.py
             "contains_medication": "MedicationDispense" in resource_types,
+            "contains_encounter": "Encounter" in resource_types,
```

To see which change mattered, I ran the flag on its own first:

| Live routing run | Accuracy | 3+ Condition Bundles correct |
| --- | ---: | ---: |
| Original | 0.814 | 0 of 11 |
| Flag only | 0.863 | 4 of 11 |
| Flag and new question | 0.951 | 11 of 11 |

Fourteen rows improved and none got worse. The question did most of the work, which I did not expect. It was one sentence, and it had been costing more than the missing data.

The rule baseline stayed the same, and a test confirms it does not use the new field. In the final run Jev was right on three Bundles the rules got wrong, and the reverse never happened. That margin is small, so I would not read it as a clear win. The rules scored 0.922 with no model at all.

Five mixed Bundles are still wrong, and three of those are at 0.87 confidence or higher, so the floor does not catch them. One of them, `vitals_only`, has a label I have not settled. The rules' 0.95 on generated Bundles also needs care: the rule checks `has_encounter_reference`, and my generator links every generated encounter Bundle that way, so the two share a signal.

## Where each side won

Jev did best where the decision depends on more than one field. On the 14 hard Condition fixtures it scored 0.929 against 0.357 for the rules. The rules reported a refuted dengue case and a cholera record marked `entered-in-error` as real. Jev confirmed neither, and both went to review. It also caught dengue and tuberculosis coded only in SNOMED, which an ICD-10 lookup cannot see.

Some of that gap is cheap to close. Prefix matching would handle subcodes like `A15.0`, and checking `verificationStatus` would handle the refuted case. A serious rule set would do both.

For routing, the rules remain the sensible default. They are simple and free, and a model can act as a second opinion, with disagreements going to a person.

Quality scoring is the weakest result. Of 45 records that needed review, Jev let 14 through and the rules let 32 through. But Jev also held 10 of 26 good records, and the rules held none.

## Confidence only works where it is calibrated

A threshold is only useful if confidence means something, so the benchmark buckets decisions by confidence and compares that with observed accuracy. This is the top bucket:

| Decision | Count | Mean confidence | Observed accuracy |
| --- | ---: | ---: | ---: |
| Notifiable | 17 | 0.844 | 1.000 |
| Routing | 84 | 0.982 | 0.964 |
| Quality | 24 | 0.825 | 0.667 |

Notifiable looks trustworthy here, and routing improved after the question change, from 0.918 in this bucket. Quality does not: a confidence of 0.82 was right about two times in three, so I would not automate anything on that threshold yet.

## What it gets wrong

**Latency.** My target was a p50 under 30 ms. The live p50 was about 235 ms for routing and notifiable, and 458 ms for quality, where a Patient takes two calls. The p95 ranged from 263 ms to 510 ms. These are client-side round trips from my machine, so they include the network, and I have not separated model time. The fast-decision premise is not proven by this data.

**Cost target.** The full run used 147,401 tokens for about $0.006. That is about $0.03 per 1,000 records, three times my $0.01 target. It is still very cheap.

**Evaluation quality.** No human has approved the labels yet. 124 are pending review, and the other 80 are correct by construction because a generator produced them. The hard sets are small. I also made both fixes after seeing these same fixtures fail, so 0.935 and 0.951 are not held-out results. They need confirming on data the system has not seen.

## What comes next

The first step is human review of the labels, because every number here depends on them. After that I want a held-out set for the notifiable and routing decisions, and a latency measurement that separates the network from the model. Two gaps from this work are still open: `ObservationSerializer` drops `code.text` the same way the Condition serializer did, and all the serializers read only the first `coding`.

The result I would keep is the shape of the system, more than any single score: parse first, flatten to a state a person can inspect, use a threshold per decision, give uncertain cases a lane, and keep a baseline that can beat the model. That baseline did beat it, and that is why I went looking. Before blaming a model, I now check what it actually received and what I actually asked.

---

*I work on clinical data systems at a research unit, mostly FHIR R4, HL7 v2, and HAPI FHIR. This is a proof of concept for a typed decision layer over FHIR records: [REPO LINK].*

<!--
Before publishing (remove this block):
1. Replace [REPO LINK], and push the repo if readers should see this code.
2. Upload docs/dev-to-images/pipeline.png and notifiable-bands.png in the dev.to editor and replace both image paths. dev.to does not render Mermaid.
3. Add the demo video if wanted. dev.to embeds YouTube links with: {% embed VIDEO_URL %}
4. Confirm TypeSafe AI is happy for these results to be published.
5. Cross-link: consider one sentence linking to https://dev.to/budiwidhiyanto/fhir-r4-for-ai-engineers-what-actually-lives-in-a-patient-record-1839

Numbers: live reports bench_20261031T150439Z (first run), bench_20261101T001036Z (after the code.text fix) and bench_20261101T054220Z (final). The flag-only routing run was a throwaway script, so 0.863 and 4 of 11 have no committed report.

Cover image prompt (use your shared style block from FHIR_RAG/docs/article-dev.to/cover-image-prompts.md):
A horizontal flow of small document cards passing through a thin gate, then splitting into four labelled lanes, with one lane highlighted in amber for human review.
-->
