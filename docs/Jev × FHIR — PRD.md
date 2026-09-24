# Jev × FHIR Decision Layer — PRD

Sep 23, 2026 · @budi

## Overview

This project builds a proof-of-concept decision layer that sits between a FHIR R4 server and downstream clinical workflows. It uses Typesafe AI's Jev model — a non-autoregressive "System 1" decision engine — to make fast, structured judgments on FHIR resources without generating text.

The core hypothesis: clinical data pipelines are full of decision points (routing, scoring, gating) that are too nuanced for hard-coded rules but don't need the latency and cost of a full LLM call. Jev's three primitives (Choice, Score, Noul) map naturally onto these decisions when the input is already structured FHIR data.

This is an exploration/portfolio project, not a production system. The output is a working prototype, benchmarks comparing Jev vs. rule-based approaches, and a publishable write-up.

## Goals

1. **Validate the Jev + FHIR pattern** — Prove that Jev can make useful clinical decisions on structured FHIR resources with measurable accuracy and sub-50ms latency.
2. **Build three working modules** — FHIR Resource Quality Scorer, Bundle Router, and Notifiable Disease Detector, each using a different Jev primitive.
3. **Benchmark against baselines** — Compare Jev decisions to hand-coded rule-based approaches on accuracy, latency, and maintainability.
4. **Produce portfolio artifacts** — Working code repository, benchmark results, and a publishable technical write-up.
5. **Demonstrate the two-layer architecture** — Show how Jev (fast decisions) and LLM (deep reasoning) complement each other in a FHIR pipeline.

## Non-Goals

- **Not production-ready** — No deployment to SPHERES or any live system. No SLA, no uptime guarantees.
- **Not a complete CDS system** — This is a decision layer, not a full clinical decision support platform.
- **Not training a custom model** — We use Jev's API as-is, no fine-tuning or custom model training.
- **Not handling PHI** — All data is synthetic (Synthea-generated). No real patient data touches this prototype.
- **Not replacing existing SPHERES logic** — This runs independently alongside, not integrated into, the SPHERES pipeline.

## Use Cases

### UC-1: FHIR Resource Quality Scoring

**As a** data engineer processing incoming FHIR resources, **I want** each Patient/Observation resource scored for completeness and validity, **so that** I can auto-accept high-quality resources and queue low-quality ones for review.

**Acceptance Criteria:**

- Given a FHIR Patient resource with all required fields populated, the scorer returns a quality score ≥ 80 with confidence ≥ 0.7
- Given a Patient resource missing `identifier`, `birthDate`, or `name`, the scorer returns a quality score ≤ 50
- Given a Patient with an invalid Indonesian NIK format, the Noul gate returns `false` with confidence ≥ 0.8
- Scoring completes in < 100ms per resource
- Scores are logged with the resource reference and timestamp

### UC-2: FHIR Bundle Routing

**As a** FHIR ingestion service, **I want** incoming Bundles automatically routed to the correct processing pipeline, **so that** I don't need to maintain brittle content-type parsing rules.

**Acceptance Criteria:**

- Given a Bundle containing lab Observation resources, the router returns `lab_result` as the chosen category
- Given a Bundle containing Encounter + Condition resources, the router returns `encounter_summary`
- Given a Bundle containing Immunization resources, the router returns `immunization_report`
- Given an ambiguous or malformed Bundle, the router returns `unknown` with confidence < 0.5, triggering a human review queue
- Routing categories are declared upfront as a fixed enum: `lab_result | encounter_summary | immunization_report | medication_dispense | unknown`
- Routing completes in < 50ms per Bundle

### UC-3: Notifiable Disease Detection

**As a** public health surveillance system, **I want** incoming Condition resources automatically checked against notifiable disease criteria, **so that** reportable cases are flagged without waiting for manual clinician review.

**Acceptance Criteria:**

- Given a Condition resource with ICD-10 code A83.0 (Japanese encephalitis), the detector returns `true` with confidence ≥ 0.9
- Given a Condition with a non-notifiable code (e.g., J06.9 — acute upper respiratory infection), the detector returns `false` with confidence ≥ 0.8
- Given a Condition with an ambiguous or rare code, confidence < 0.6 triggers human review
- Detection completes in < 50ms per Condition resource
- Positive detections are logged as a FHIR Flag resource referencing the original Condition

## Functional Requirements

### FR-1: Resource Serializer

A module that converts FHIR R4 resources into Jev-compatible input format.

- FR-1.1: Accept any FHIR R4 resource as JSON input
- FR-1.2: Extract decision-relevant fields based on resource type (Patient: identifier, name, birthDate, gender, address, telecom; Observation: code, value, status, effectiveDateTime, subject reference; Condition: code, clinicalStatus, verificationStatus, subject reference; Bundle: entry types, entry count, total)
- FR-1.3: Output a flat key-value structure suitable for Jev's input format
- FR-1.4: Handle missing fields gracefully — include them as `null` or `missing` rather than failing

### FR-2: Quality Scorer Module

- FR-2.1: Accept a serialized FHIR resource and call Jev **Score** with a completeness question
- FR-2.2: Define scoring scale: 0–100, where 100 = all expected fields present and valid
- FR-2.3: Return `{score: int, confidence: float, missing_fields: list[str], resource_reference: str}`
- FR-2.4: Support configurable threshold — above threshold = auto-accept, below = review queue

### FR-3: Bundle Router Module

- FR-3.1: Accept a serialized FHIR Bundle and call Jev **Choice** with declared categories
- FR-3.2: Categories enum: `lab_result`, `encounter_summary`, `immunization_report`, `medication_dispense`, `unknown`
- FR-3.3: Return `{category: str, confidence: float, probabilities: dict[str, float], bundle_id: str}`
- FR-3.4: Bundles with top-choice confidence < 0.5 must be routed to `unknown`

### FR-4: Notifiable Disease Detector Module

- FR-4.1: Accept a serialized Condition resource and call Jev **Noul** with the notifiable disease question
- FR-4.2: Reference list: Indonesian notifiable diseases mapped to ICD-10 codes (initial set: A00–A09 cholera/typhoid, A15–A19 TB, A30 leprosy, A83 Japanese encephalitis, A90–A91 dengue, B50–B54 malaria, B20 HIV)
- FR-4.3: Return `{is_notifiable: bool, probability: float, condition_code: str, condition_display: str}`
- FR-4.4: Generate a FHIR Flag resource for positive detections with `Flag.code` referencing the notifiable disease regulation

### FR-5: Decision Logger

- FR-5.1: Every Jev decision is logged as a structured JSON record: timestamp, module, resource\_reference, decision, confidence, latency\_ms
- FR-5.2: Optionally emit a FHIR AuditEvent resource for each decision
- FR-5.3: Logs are queryable for benchmarking and analysis

## Non-Functional Requirements

- **NFR-1: Latency** — Jev API calls must complete in < 100ms p95. End-to-end per-resource processing (serialize + decide + log) must complete in < 200ms p95.
- **NFR-2: Accuracy** — Quality Scorer must achieve ≥ 85% agreement with hand-labeled ground truth on a 50-resource test set. Bundle Router must achieve ≥ 90% accuracy on a 100-bundle test set. Notifiable Disease Detector must achieve ≥ 95% recall (false negatives are the critical failure mode).
- **NFR-3: Observability** — All decisions logged with latency, confidence, and input hash. Expose a `/metrics` endpoint with counters per module, per decision category, and latency histograms.
- **NFR-4: Data constraints** — Zero real patient data. All test data from Synthea or hand-crafted fixtures. No PHI in logs, configs, or API calls.
- **NFR-5: Reproducibility** — Fixed random seeds where applicable. Pinned Jev API version. All test fixtures committed to the repo. Benchmark results reproducible from a single `make bench` command.
- **NFR-6: Cost** — At $42/billion input tokens, a 100-resource benchmark run should cost effectively nothing (< $0.01). Log token counts per call for cost tracking.

## API Contract

### POST /api/v1/quality-score

**Request:**

```json
{
  "resource_type": "Patient",
  "resource": { /* FHIR R4 Patient JSON */ },
  "threshold": 70
}
```

**Response:**

```json
{
  "score": 85,
  "confidence": 0.92,
  "level": "acceptable",
  "missing_fields": ["telecom"],
  "resource_reference": "Patient/12345",
  "latency_ms": 47,
  "action": "auto_accept"
}
```

### POST /api/v1/route-bundle

**Request:**

```json
{
  "bundle": { /* FHIR R4 Bundle JSON */ }
}
```

**Response:**

```json
{
  "category": "lab_result",
  "confidence": 0.94,
  "probabilities": {
    "lab_result": 0.94,
    "encounter_summary": 0.03,
    "immunization_report": 0.01,
    "medication_dispense": 0.01,
    "unknown": 0.01
  },
  "bundle_id": "Bundle/abc-123",
  "latency_ms": 32
}
```

### POST /api/v1/detect-notifiable

**Request:**

```json
{
  "condition": { /* FHIR R4 Condition JSON */ }
}
```

**Response:**

```json
{
  "is_notifiable": true,
  "probability": 0.97,
  "condition_code": "A83.0",
  "condition_display": "Japanese encephalitis",
  "flag_resource": { /* generated FHIR Flag JSON */ },
  "latency_ms": 28
}
```

### GET /api/v1/metrics

Returns Prometheus-compatible metrics: request counts, latency histograms, confidence distributions, and Jev API token usage per module.

## Success Metrics

| Metric | Target | How to Measure |
| --- | --- | --- |
| Quality Scorer accuracy | ≥ 85% agreement with ground truth | Hand-label 50 resources, compare |
| Bundle Router accuracy | ≥ 90% correct routing | Hand-label 100 bundles, compare |
| Notifiable Disease recall | ≥ 95% | Ensure all known-notifiable test cases are caught |
| Notifiable Disease precision | ≥ 80% | Measure false positive rate |
| Jev API latency p50 | < 30ms | Measured from decision logs |
| Jev API latency p95 | < 100ms | Measured from decision logs |
| End-to-end latency p95 | < 200ms | Measured from API endpoint |
| Confidence calibration | Predicted confidence ≈ actual accuracy | Bucket decisions by confidence, check accuracy per bucket |
| Cost per 1000 decisions | < $0.01 | Token count from logs × Jev pricing |

## Open Questions & Risks

**Open Questions:**

1. **Jev input format** — The exact schema for Jev's API input is not fully documented yet. We need to test what level of structured data it can reason about. Can it handle nested FHIR references, or does everything need to be flattened?
2. **Context window** — How much of a FHIR resource can we send to Jev per decision? A Bundle can be large — do we need to summarize first?
3. **Custom question phrasing** — How sensitive is Jev to how we phrase the decision question? Does "Is this a notifiable disease under Indonesian regulation?" perform differently from "Should this condition trigger a public health alert?"
4. **Indonesian context** — Jev is trained on general data. How well does it handle Indonesian-specific clinical coding and regulatory context?
5. **Versioning** — Jev is on v1.13 in early access. API stability is unknown.

**Risks:**

- **API access** — Early access could be waitlisted or rate-limited. Mitigation: sign up immediately, have a mock Jev client as fallback for development.
- **Accuracy on clinical data** — Jev may not have enough healthcare training data for reliable clinical decisions. Mitigation: benchmark honestly, report failures, don't overstate results.
- **API instability** — Breaking changes in early access. Mitigation: pin the API version, abstract behind a client interface.
- **Scope creep** — Easy to keep adding use cases. Mitigation: strict three-module scope, timebox to three nights/weekend sessions.
