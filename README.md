# Jev × FHIR Decision Layer

A proof-of-concept decision layer that puts [TypeSafe AI's Jev](https://typesafe.ai) — a
non-generative "System 1" decision model — in front of FHIR R4 clinical workflows. It scores
resource quality, routes FHIR Bundles, and detects Indonesian notifiable diseases, returning
typed decisions with probabilities instead of generated text. All data is synthetic.

> **Status:** exploration / portfolio project. Phases 1–5 (client, serializers, decision
> modules, API, benchmarks) are complete. A web demo UI is planned — see
> [Demo Plan](docs/Jev%20×%20FHIR%20—%20Demo%20Plan%20Requirement.md). Not for production use.

## Why

Clinical data pipelines are full of small decisions — *is this record good enough? where
does this Bundle go? must this be reported?* Hard-coded rules are brittle; full LLM calls are
slow, expensive, and need output parsing. Jev's three primitives map directly onto these
decisions when the input is already structured FHIR:

| Module | Jev primitive | Question it answers | Action |
| --- | --- | --- | --- |
| Quality Scorer | **Score** (0–100) + **Noul** | How complete/valid is this Patient or Observation? Is the NIK a valid 16-digit Indonesian ID? | `auto_accept` or `review_needed` |
| Bundle Router | **Choice** | Is this Bundle `lab_result`, `encounter_summary`, `immunization_report`, `medication_dispense`, or `unknown`? | Route; low confidence → `unknown` |
| Notifiable Disease Detector | **Noul** (yes/no) | Must this Condition be reported to Indonesian public health authorities? | FHIR `Flag` for confirmed cases |

## Architecture

```text
FHIR R4 JSON (Patient · Observation · Condition · Bundle)
    │
    ▼
FHIR serializers ──► flat decision state ──► Jev client (mock or live SDK)
    │                                           │
    ├── Quality Scorer                          ├── Score
    ├── Bundle Router                           ├── Choice
    └── Notifiable Disease Detector             └── Noul
                                                    │
                                                    ▼
                          threshold policy ──► FastAPI response
                                               + FHIR Flag (notifiable)
                                               + structured decision log
                                               + Prometheus metrics
```

Jev never sees raw FHIR: serializers flatten each resource into a small key/value state
(`has_identifier`, `identifier_value_length`, `code_value`, `dominant_resource_type`, …).
Confidence thresholds decide what is automated and what goes to a human.

## Quick start (offline, mock Jev)

Requires Python 3.11+.

```bash
git clone https://github.com/budityw23/fhir_jev.git
cd fhir_jev
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env          # MOCK_JEV=true by default
make serve
```

The API listens on `http://127.0.0.1:8000`; interactive docs are at
`http://127.0.0.1:8000/docs`.

In mock mode, `MockJevClient` returns deterministic decisions with simulated 10–30 ms
latency and makes no network calls. Tests and `make bench` always use it.

## Live Jev mode

1. Get an API key from TypeSafe AI.
2. Edit `.env` (never commit it — it is git-ignored):

   ```dotenv
   JEV_API_KEY=<your key>
   MOCK_JEV=false
   ```

3. `make serve`, then check `curl http://127.0.0.1:8000/health` reports `"jev_client": "live"`.

The live client uses the official `typesafe-sdk` (`AsyncTypeSafeClient.system_one`) with the
`jev-latest` model.

## Configuration

Environment variables (loaded from `.env`):

| Variable | Default | Description |
| --- | --- | --- |
| `JEV_API_KEY` | `mock-key` | TypeSafe API key (live mode only) |
| `JEV_BASE_URL` | `https://api.typesafe.ai` | SDK base URL; a legacy `/v1/` suffix is accepted |
| `MOCK_JEV` | `false` | `true` uses the offline mock client |
| `LOG_LEVEL` | `INFO` | Log level |

## API

All examples below are real responses from mock mode. Live values will differ.

### `POST /api/v1/quality-score`

Scores a `Patient` or `Observation`. Patients also get a NIK validity check.
`threshold` (0–100, default 70): `score >= threshold` → `auto_accept`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/quality-score \
  -H 'content-type: application/json' \
  -d '{"resource_type":"Patient","resource":{"resourceType":"Patient","id":"example"},"threshold":70}'
```

```json
{
  "score": 0,
  "confidence": 0.88,
  "level": "review_needed",
  "missing_fields": ["identifier", "name", "birthDate", "gender", "address", "telecom"],
  "nik_valid": false,
  "nik_confidence": 0.92,
  "resource_reference": "Patient/example",
  "latency_ms": 33.586,
  "action": "review_needed"
}
```

A complete patient (`tests/fixtures/patients/complete_patient.json`) returns
`score: 80`, `nik_valid: true`, `missing_fields: ["telecom"]`, `action: "auto_accept"`.

### `POST /api/v1/route-bundle`

Routes a Bundle to one of the fixed categories. Top-choice confidence below 0.5 is
overridden to `unknown`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/route-bundle \
  -H 'content-type: application/json' \
  -d "{\"bundle\": $(cat tests/fixtures/bundles/lab_bundle.json)}"
```

```json
{
  "category": "lab_result",
  "confidence": 0.92,
  "probabilities": {
    "lab_result": 0.92,
    "encounter_summary": 0.02,
    "immunization_report": 0.02,
    "medication_dispense": 0.02,
    "unknown": 0.02
  },
  "bundle_id": "lab-bundle",
  "latency_ms": 31.149
}
```

### `POST /api/v1/detect-notifiable`

Checks a `Condition` against Indonesian notifiable diseases
([`data/notifiable_diseases.json`](data/notifiable_diseases.json): cholera, typhoid, TB,
leprosy, Japanese encephalitis, dengue, malaria, HIV). The Condition must be valid FHIR R4
(`clinicalStatus` and `subject` included).

| Probability | Status | Flag |
| --- | --- | --- |
| ≥ 0.8 and answer = yes | `confirmed_notifiable` | FHIR `Flag` generated |
| 0.5 – 0.8 | `review_needed` | — |
| < 0.5 | `not_notifiable` | — |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect-notifiable \
  -H 'content-type: application/json' \
  -d '{"condition":{"resourceType":"Condition","id":"example",
       "clinicalStatus":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/condition-clinical","code":"active"}]},
       "code":{"coding":[{"system":"http://hl7.org/fhir/sid/icd-10","code":"A90","display":"Dengue fever"}]},
       "subject":{"reference":"Patient/12345"}}}'
```

```json
{
  "is_notifiable": true,
  "probability": 0.95,
  "status": "confirmed_notifiable",
  "condition_code": "A90",
  "condition_display": "Dengue fever",
  "flag_resource": {
    "resourceType": "Flag",
    "status": "active",
    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/flag-category", "code": "clinical"}]}],
    "code": {
      "coding": [{"system": "http://snomed.info/sct", "code": "281269004", "display": "Notifiable disease"}],
      "text": "Dengue fever (A90) - mandatory reporting"
    },
    "subject": {"reference": "Patient/12345"},
    "period": {"start": "2026-09-24"}
  },
  "latency_ms": 18.883
}
```

### `GET /health`

```json
{"status": "ok", "jev_client": "mock", "version": "0.1.0"}
```

### `GET /api/v1/metrics`

Prometheus exposition format:

| Metric | Labels |
| --- | --- |
| `jev_fhir_http_requests_total` | `endpoint`, `method`, `status` |
| `jev_fhir_http_request_duration_seconds` | `endpoint` |
| `jev_fhir_decisions_total` | `module`, `decision` |
| `jev_fhir_decision_confidence` | `module` |

### Errors

Every error returns the same body, with the request id also sent in the `X-Request-Id`
header:

```json
{
  "error": "invalid_request",
  "detail": "Unsupported resource type for quality scoring: Condition",
  "request_id": "8df84f31-de2c-4fd3-9f02-e43592596f38",
  "timestamp": "2026-09-24T13:58:28.245130Z"
}
```

| Status | `error` | Cause |
| --- | --- | --- |
| 400 | `invalid_request` | Wrong resource type for the endpoint, or `resource_type` mismatch |
| 422 | `validation_error` | Malformed request body or invalid FHIR R4 resource |
| 502 | `jev_error` | Live Jev SDK call failed (network, auth, rate limit, timeout) |

Every response also carries `X-Request-Duration-Ms`.

## Observability

- **Decision log:** every decision is logged as one JSON line (structlog) with `timestamp`,
  `module`, `resource_reference`, `decision`, `confidence`, and `latency_ms`. No clinical
  content is logged.
- **Metrics:** see `/api/v1/metrics` above.
- **AuditEvent:** `fhir_helpers/audit_event.py` builds a FHIR R4 `AuditEvent` per decision
  (library only; not yet emitted by the API).

## Benchmarks

```bash
make bench
```

Runs all 50 hand-labelled fixtures (20 Patients, 15 Conditions, 15 Bundles) through both the
Jev modules and rule-based baselines ([`benchmarks/baselines/`](benchmarks/baselines/)), then
writes `benchmarks/results/bench_<timestamp>.{json,md}` with accuracy, precision/recall/F1,
latency (mean/p50/p95), and confidence calibration.

Latest report (mock Jev, Sep 24, 2026):

| Module | Fixtures | Jev accuracy | Rule accuracy | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality Scorer | 20 | 1.000 | 1.000 | 44.7 | 53.1 |
| Bundle Router | 15 | 0.733 | 0.933 | 28.4 | 40.6 |
| Notifiable Detector | 15 | 1.000 | 1.000 | 19.7 | 29.8 |

**How to read this:** these numbers come from the **mock** client, which uses rule-like
logic, so they validate the harness, not Jev. The mock misroutes four ambiguous bundles
(empty, patient-only, nested, mixed) because its fallback confidence never drops below the
0.5 `unknown` floor. A live-Jev benchmark is planned (see *Known limitations*).

## Development

```bash
make lint        # ruff check + format check
make typecheck   # mypy --strict
make test        # pytest with coverage (48 tests, ~97% coverage)
make bench       # mock benchmark report
make serve       # uvicorn on 127.0.0.1:8000
```

Tests never call the live API. The live client is tested against a mocked `typesafe-sdk`.

## Project structure

```text
src/jev_fhir/
├── main.py              FastAPI app, middleware (request id, timing), error handlers
├── config.py            Settings from environment / .env
├── dependencies.py      dependency injection (AppServices)
├── logger.py            structured decision logging
├── metrics.py           Prometheus counters and histograms
├── jev_client/          JevClient interface, live SDK client, deterministic mock
├── serializer/          FHIR R4 → flat decision state (Patient, Observation, Condition, Bundle)
├── modules/             quality_scorer, bundle_router, notifiable_detector
├── fhir_helpers/        Flag and AuditEvent builders
└── routes/              API endpoints
tests/                   unit + API tests; fixtures/ holds 50 synthetic FHIR R4 resources
data/                    Indonesian notifiable-disease reference list (ICD-10)
benchmarks/              ground truth, rule baselines, runner, generated reports
docs/                    idea, PRD, technical plan, phase plan, demo plan
```

## Data and privacy

No real patient data. Every fixture is hand-crafted synthetic FHIR R4, and NIKs are
fabricated. In live mode only the flattened decision state is sent to Jev: field-presence
flags, codes, counts, identifier *length* (not the value), address country, and the
patient's family name. Remove `name_family` from `serializer/patient.py` before using this
with anything other than synthetic data.

## Known limitations

- **Mock ≠ Jev.** Mock decisions mirror rule logic; the benchmark above is not evidence
  of Jev's accuracy.
- **Benchmarks are mock-only.** `bench_runner.py` does not yet accept a live client.
- **Quality ground truth is point-valued** (e.g. exactly 80) and matches the mock's formula;
  it needs banded labels before a live benchmark is meaningful.
- **Noul probability semantics** differ between the mock NIK check (confidence in the answer)
  and the live client (probability the statement is true).
- **Live error handling** maps all SDK failures to `502 jev_error`; the SDK's default timeout
  (10 s, with retries) is used.
- **Thresholds** for routing and notifiable detection are not yet exposed as request
  parameters.

Fixes for all of these are planned in Phase D0 of the
[Demo Plan](docs/Jev%20×%20FHIR%20—%20Demo%20Plan%20Requirement.md).

## Documentation

- [Idea Exploration](docs/Jev%20×%20FHIR%20Idea%20Exploration.md): motivation and use cases
- [PRD](docs/Jev%20×%20FHIR%20—%20PRD.md): goals, use cases, requirements, success metrics
- [Technical Implementation Plan](docs/Jev%20×%20FHIR%20—%20Technical%20Implementation%20Plan.md)
- [Phases](docs/Jev%20×%20FHIR%20—%20Phases.md): phase-by-phase build and evaluation log
- [Demo Plan & UI Requirements](docs/Jev%20×%20FHIR%20—%20Demo%20Plan%20Requirement.md)

## Tech stack

Python 3.11+, FastAPI, Pydantic v2, `fhir.resources`, `typesafe-sdk`, structlog,
prometheus-client, pytest, Ruff, mypy (strict).

## License

[MIT](LICENSE)
