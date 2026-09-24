# Jev × FHIR: Idea Exploration

Sep 22, 2026 · @budi

## The Core Idea

Most clinical software is a giant decision tree: route this patient, flag this lab, triage this encounter, validate this resource. Today those decisions are either hard-coded rules or full LLM calls — one is brittle, the other is slow and expensive.

Jev sits in the gap. Its three primitives map cleanly onto FHIR workflows:

- **Choice** — pick one option from a declared set (route a FHIR Bundle to the right pipeline, select a CDS recommendation)
- **Score** — rate something on a defined scale (urgency of an Encounter, data quality of a Patient resource, completeness of an Observation set)
- **Noul** — answer a yes/no gate (does this Condition indicate a notifiable disease? is this MedicationRequest a duplicate?)

Each returns probabilities and confidence — not prose. No prompt engineering, no output parsing, no retries on malformed JSON. Just a typed decision you can act on in code.

The FHIR angle is especially interesting: FHIR resources are already structured data with well-defined semantics. Jev doesn't need to understand free text — it evaluates structured clinical state and makes a judgment. That's exactly what "System 1" thinking is for.

## Use Cases

### 1. FHIR Bundle Routing

A SPHERES-like federated system receives Bundles from multiple provinces. Before expensive validation or transformation, Jev **Choice** could route each Bundle: `lab_result | encounter_summary | immunization_report | unknown`. Confidence below threshold → queue for human review. This replaces brittle content-type parsing with contextual routing.

### 2. Clinical Data Quality Scoring

Every incoming Patient or Observation resource gets a Jev **Score** for completeness: is the identifier present? are required codings from the correct ValueSet? does the Observation have a proper reference to its Encounter? Returns a 0–100 quality score with confidence — feed it into a dashboard or use it to gate which resources proceed to analytics.

### 3. Notifiable Disease Detection

When a Condition resource arrives, Jev **Noul** answers: "Is this a notifiable disease under Indonesian regulation?" Binary yes/no with probability. High-confidence positives trigger an automated alert to Dinkes. Low-confidence cases get flagged for clinical review. Much faster than waiting for a clinician to manually flag.

### 4. CDS Hooks Pre-filter

CDS Hooks fire on every clinical event — most are noise. Jev **Choice** sits in front: for each hook trigger, decide `show_alert | suppress | escalate`. Only meaningful alerts reach the clinician. This is the "cheap decision layer in front of expensive reasoning" pattern.

### 5. Duplicate Resource Detection

Patient matching across facilities is a classic problem. Jev **Noul** on pairs of Patient resources: "Are these the same person?" with confidence. High confidence → auto-merge. Medium → human review queue. Low → separate records.

## Architecture Sketch

The pattern is **Jev as triage layer, LLM as reasoning layer, FHIR server as source of truth**.

```
FHIR Server (HAPI)
    │
    ▼
Ingestion Service (FastAPI)
    │
    ├──► Jev API ──► Decision (Choice/Score/Noul)
    │                    │
    │         ┌──────────┴──────────┐
    │         ▼                    ▼
    │    High confidence       Low confidence
    │    → auto-act            → queue / escalate
    │         │                    │
    │         ▼                    ▼
    │    Direct FHIR write    LLM reasoning layer
    │    (update, flag,       (Claude API for
    │     route, alert)        complex analysis)
    │                              │
    │                              ▼
    │                         Human review
    │                         dashboard
    └──────────────────────────────┘
```

**Key architectural decisions:**

- Jev handles the high-volume, low-latency decisions ("is this valid?", "where does this go?", "is this urgent?")
- Claude/LLM handles the long-tail cases where Jev's confidence is low and real reasoning is needed
- The FHIR server remains the single source of truth — Jev never mutates data, only makes routing/scoring decisions
- The confidence threshold is the control knob: lower it → more automation, higher it → more human review
- All decisions are logged as AuditEvent resources back to the FHIR server for traceability

## Weekend Prototype Plan

**Goal:** Build the smallest thing that proves Jev + FHIR works — a FHIR resource quality scorer.

### Night 1: Setup & Jev Hello World

- Sign up for Jev early access at Typesafe AI
- Get API key, test the three primitives with simple examples
- Set up a Python project with FastAPI skeleton
- Load a few synthetic FHIR Patient resources (use Synthea or HAPI's test data)

### Night 2: FHIR Quality Scorer

- Write a function that serializes a FHIR Patient resource into Jev-friendly input (key fields: identifier, name, birthDate, address, telecom)
- Call Jev **Score** to rate completeness (0–100)
- Call Jev **Noul** to check: "Does this Patient have a valid Indonesian NIK?"
- Log results, compare with a hand-coded rule-based scorer

### Night 3: Bundle Router

- Stand up a minimal FHIR endpoint that receives Bundles
- Jev **Choice** routes each Bundle to a category
- Compare latency and accuracy vs. a simple regex/rule-based router
- Write up findings

### Stack

- Python 3.11+, FastAPI, httpx (for Jev API calls)
- HAPI FHIR test server or local Docker instance
- Synthea for synthetic patient data
- Jev API (early access)

### Data

- Synthea-generated Indonesian patient profiles (or adapt SPHERES test data if non-sensitive)
- Mix of complete and incomplete resources to test quality scoring
- A handful of notifiable disease Condition resources for the Noul gate test

## Portfolio Angle

This exploration hits several marks for international positioning:

- **Cutting-edge + domain depth** — Jev is brand new (Sep 2026 early access). Being among the first to apply it to healthcare/FHIR signals you're tracking the frontier, not just following tutorials.
- **Complements the FHIR RAG project** — RAG handles the "System 2" reasoning (clinical Q&A over patient data). Jev handles the "System 1" decisions (triage, routing, scoring). Together they tell the story: "I build intelligent FHIR pipelines with the right AI tool for each job."
- **Publishable** — A dev.to post like *"Jev × FHIR: Using Decision Models for Clinical Data Quality"* would be novel content. Nobody has written this yet.
- **Demo-able** — A working quality scorer or bundle router is a concrete artifact you can show in interviews. "Here's a FHIR resource, watch Jev score it in 5ms with 94% confidence" is more compelling than slides.
- **Architecture thinking** — The two-layer pattern (Jev for fast decisions, LLM for reasoning) shows you think about cost, latency, and system design — exactly what senior/staff engineers are hired for.

**Risk:** Jev is early-stage. The API could change, documentation is sparse, and production readiness is unknown. This is strictly exploration and portfolio material — not something to ship into SPHERES tomorrow.
