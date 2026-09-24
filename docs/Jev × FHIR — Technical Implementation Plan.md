# Jev × FHIR — Technical Implementation Plan

Sep 23, 2026 · @budi

## Project Structure

```
jev-fhir/
├── README.md
├── pyproject.toml
├── Makefile                    # dev commands: lint, test, bench, serve
├── .env.example                # JEV_API_KEY, JEV_BASE_URL, FHIR_SERVER_URL
├── src/
│   └── jev_fhir/
│       ├── __init__.py
│       ├── main.py             # FastAPI app entry point
│       ├── config.py           # Settings via pydantic-settings
│       ├── serializer/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract serializer interface
│       │   ├── patient.py      # Patient resource serializer
│       │   ├── observation.py  # Observation resource serializer
│       │   ├── condition.py    # Condition resource serializer
│       │   └── bundle.py       # Bundle resource serializer
│       ├── jev_client/
│       │   ├── __init__.py
│       │   ├── client.py       # Jev API wrapper (httpx async)
│       │   ├── models.py       # Pydantic models for Jev I/O
│       │   └── mock.py         # Mock client for dev/testing
│       ├── modules/
│       │   ├── __init__.py
│       │   ├── quality_scorer.py
│       │   ├── bundle_router.py
│       │   └── notifiable_detector.py
│       ├── fhir_helpers/
│       │   ├── __init__.py
│       │   ├── flag_builder.py     # Builds Flag resources
│       │   └── audit_event.py      # Builds AuditEvent resources
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── quality.py
│       │   ├── routing.py
│       │   ├── notifiable.py
│       │   └── metrics.py
│       └── logger.py           # Structured decision logger
├── tests/
│   ├── conftest.py
│   ├── fixtures/               # Static FHIR JSON test data
│   │   ├── patients/
│   │   ├── observations/
│   │   ├── conditions/
│   │   └── bundles/
│   ├── test_serializer.py
│   ├── test_jev_client.py
│   ├── test_quality_scorer.py
│   ├── test_bundle_router.py
│   ├── test_notifiable_detector.py
│   └── test_api.py
├── benchmarks/
│   ├── bench_runner.py         # Benchmark harness
│   ├── ground_truth/           # Hand-labeled expected results
│   ├── baselines/              # Rule-based comparison implementations
│   └── results/                # Benchmark output (gitignored)
└── data/
    ├── synthea/                # Generated synthetic data
    └── notifiable_diseases.json  # Indonesian notifiable disease list + ICD-10
```

## Tech Stack & Dependencies

```toml
[project]
name = "jev-fhir"
version = "0.1.0"
requires-python = ">=3.11"

[project.dependencies]
fastapi = ">=0.115.0"
uvicorn = { version = ">=0.30.0", extras = ["standard"] }
httpx = ">=0.27.0"              # Async HTTP client for Jev API
pydantic = ">=2.9.0"            # Request/response models
pydantic-settings = ">=2.5.0"   # Config from .env
fhir-resources = ">=7.1.0"      # FHIR R4 Pydantic models (fhir.resources)
structlog = ">=24.4.0"          # Structured logging
prometheus-client = ">=0.21.0"  # Metrics endpoint

[project.optional-dependencies]
dev = [
    "pytest >= 8.3.0",
    "pytest-asyncio >= 0.24.0",
    "pytest-cov >= 5.0.0",
    "httpx",                    # TestClient uses httpx
    "ruff >= 0.6.0",            # Linting + formatting
    "mypy >= 1.11.0",           # Type checking
]
```

**Runtime:**

- Python 3.11+ (match SPHERES stack)
- Docker for local HAPI FHIR server (optional — can use public test server)

**External services:**

- Jev API — `https://api.typesafe.ai/v1/` (early access, API key required)
- HAPI FHIR test server — `https://hapi.fhir.org/baseR4` (public, no auth) or local Docker `hapiproject/hapi:latest`

**Not used (by design):**

- No database — all state is in-memory or logged to files
- No message queue — synchronous request/response only
- No LLM in this prototype — Jev only (LLM layer is future work)

## Module 1: FHIR Resource Serializer

**Purpose:** Convert FHIR R4 resources into flat key-value dicts that Jev can reason about.

**Interface:**

```python
class FHIRSerializer(ABC):
    @abstractmethod
    def serialize(self, resource: dict) -> dict[str, Any]:
        """Extract decision-relevant fields from a FHIR resource."""
        ...
    
    @abstractmethod
    def resource_type(self) -> str:
        ...
```

**PatientSerializer output:**

```python
{
    "resource_type": "Patient",
    "has_identifier": True,
    "identifier_system": "nik",
    "identifier_value_length": 16,  # NIK = 16 digits
    "has_name": True,
    "name_family": "Wijaya",
    "has_birth_date": True,
    "has_gender": True,
    "has_address": True,
    "address_country": "ID",
    "has_telecom": False,
    "telecom_count": 0,
    "field_completeness": 8,  # out of 10 expected fields
    "field_total": 10
}
```

**BundleSerializer output:**

```python
{
    "resource_type": "Bundle",
    "bundle_type": "collection",
    "entry_count": 5,
    "entry_resource_types": ["Observation", "Observation", "DiagnosticReport"],
    "dominant_resource_type": "Observation",
    "has_patient_reference": True,
    "has_encounter_reference": False,
    "contains_lab_codes": True,
    "contains_condition_codes": False,
    "contains_immunization": False,
    "contains_medication": False
}
```

**ConditionSerializer output:**

```python
{
    "resource_type": "Condition",
    "code_system": "http://hl7.org/fhir/sid/icd-10",
    "code_value": "A83.0",
    "code_display": "Japanese encephalitis",
    "clinical_status": "active",
    "verification_status": "confirmed",
    "has_subject": True,
    "has_onset": True,
    "category": "encounter-diagnosis"
}
```

**Implementation notes:**

- Use `fhir.resources` Pydantic models for parsing and validation, then extract fields
- Gracefully handle missing fields — set `has_*` flags to `False` and values to `null`
- Each serializer is a separate file for testability
- The serializer must NOT call any external API — it's pure data transformation

## Module 2: Jev Client

**Purpose:** Async wrapper around the Jev API with retry logic, timeout handling, and a mock fallback for offline development.

**Interface:**

```python
class JevClient(ABC):
    async def choice(
        self,
        state: dict[str, Any],
        question: str,
        options: list[str],
    ) -> ChoiceResult:
        ...

    async def score(
        self,
        state: dict[str, Any],
        question: str,
        scale_min: int = 0,
        scale_max: int = 100,
    ) -> ScoreResult:
        ...

    async def noul(
        self,
        state: dict[str, Any],
        statement: str,
    ) -> NoulResult:
        ...
```

**Pydantic response models:**

```python
class ChoiceResult(BaseModel):
    choice: str
    confidence: float
    probabilities: dict[str, float]
    latency_ms: float
    tokens_used: int

class ScoreResult(BaseModel):
    score: int
    confidence: float
    level_probabilities: dict[str, float] | None = None
    latency_ms: float
    tokens_used: int

class NoulResult(BaseModel):
    answer: bool
    probability: float
    latency_ms: float
    tokens_used: int
```

**LiveJevClient implementation:**

- Use `httpx.AsyncClient` with connection pooling
- Base URL from `JEV_BASE_URL` env var
- API key from `JEV_API_KEY` env var, sent as Bearer token
- Timeout: 5s per request
- Retry: 2 retries with exponential backoff on 429/5xx
- Measure latency with `time.perf_counter()` around each call
- Track `tokens_used` from the API response headers/body

**MockJevClient implementation:**

- Returns deterministic results based on input hashing
- Configurable via `MOCK_JEV=true` env var
- Used for: unit tests, CI, offline development
- Simulates realistic latency (10–30ms random delay)
- Returns plausible confidence values (0.6–0.95 range)

## Module 3: Quality Scorer

**Purpose:** Score a FHIR resource's data quality using Jev Score, then validate specific fields with Jev Noul.

**Flow:**

1. Accept raw FHIR resource JSON + resource\_type
2. Dispatch to the correct serializer (PatientSerializer, ObservationSerializer)
3. Call `jev_client.score(state=serialized, question="Rate the data quality and completeness of this clinical resource from 0 (empty/invalid) to 100 (all fields present, correctly formatted, clinically complete)", scale_min=0, scale_max=100)`
4. If resource is Patient: call `jev_client.noul(state=serialized, statement="This patient has a valid 16-digit Indonesian NIK identifier")`
5. Combine results into `QualityScoreResponse`
6. Apply threshold: score ≥ threshold → `auto_accept`, else → `review_needed`
7. Log the decision

**Key design decisions:**

- The Jev question phrasing is critical — store it as a constant, not inline, so it's easy to iterate
- The NIK validation Noul is Patient-specific; other resource types skip it
- The threshold is per-request (passed in the API call) with a default of 70
- Quality scorer never modifies the resource — it's read-only scoring

## Module 4: Bundle Router

**Purpose:** Route incoming FHIR Bundles to the correct processing pipeline using Jev Choice.

**Flow:**

1. Accept raw FHIR Bundle JSON
2. Serialize with BundleSerializer
3. Call `jev_client.choice(state=serialized, question="What type of clinical data does this FHIR Bundle primarily contain?", options=["lab_result", "encounter_summary", "immunization_report", "medication_dispense", "unknown"])`
4. If top choice confidence < 0.5: override to `unknown`
5. Build `BundleRouteResponse` with full probability distribution
6. Log the decision

**Categories and their signals:**

| Category | Key serializer signals |
| --- | --- |
| `lab_result` | `dominant_resource_type` = Observation, `contains_lab_codes` = True |
| `encounter_summary` | `has_encounter_reference` = True, contains Condition resources |
| `immunization_report` | `contains_immunization` = True |
| `medication_dispense` | `contains_medication` = True |
| `unknown` | None dominant, or confidence < 0.5 |

## Module 5: Notifiable Disease Detector

**Purpose:** Check if a Condition resource represents a notifiable disease using Jev Noul, and generate a FHIR Flag resource for positive detections.

**Flow:**

1. Accept raw FHIR Condition JSON
2. Serialize with ConditionSerializer
3. Load reference list from `data/notifiable_diseases.json`
4. Call `jev_client.noul(state={**serialized, "notifiable_diseases_context": reference_list_summary}, statement="This condition is a notifiable disease that requires mandatory reporting to Indonesian public health authorities")`
5. Apply confidence thresholds: ≥ 0.8 → `confirmed_notifiable`, 0.5–0.8 → `review_needed`, < 0.5 → `not_notifiable`
6. If confirmed: generate a FHIR Flag resource via `FlagBuilder`
7. Log the decision

**`data/notifiable_diseases.json` structure:**

```json
{
  "diseases": [
    {
      "name": "Japanese Encephalitis",
      "icd10_codes": ["A83.0"],
      "category": "vector_borne",
      "reporting_urgency": "24h"
    },
    {
      "name": "Dengue",
      "icd10_codes": ["A90", "A91"],
      "category": "vector_borne",
      "reporting_urgency": "24h"
    }
  ]
}
```

**FlagBuilder output:**

```json
{
  "resourceType": "Flag",
  "status": "active",
  "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/flag-category", "code": "clinical"}]}],
  "code": {"coding": [{"system": "http://snomed.info/sct", "code": "281269004", "display": "Notifiable disease"}], "text": "Japanese encephalitis - mandatory reporting"},
  "subject": {"reference": "Patient/12345"},
  "period": {"start": "2026-09-23"}
}
```

## Module 6: FastAPI Application

**Entry point:** `src/jev_fhir/main.py`

```python
app = FastAPI(
    title="Jev × FHIR Decision Layer",
    version="0.1.0",
    description="Proof-of-concept: Jev AI decision primitives for FHIR clinical workflows",
)
```

**Endpoints:**

- `POST /api/v1/quality-score` → `routes/quality.py`
- `POST /api/v1/route-bundle` → `routes/routing.py`
- `POST /api/v1/detect-notifiable` → `routes/notifiable.py`
- `GET /api/v1/metrics` → `routes/metrics.py` (Prometheus format)
- `GET /health` → health check (returns Jev API connectivity status)

**Startup:**

- Initialize `JevClient` (Live or Mock based on config)
- Initialize all serializers
- Initialize all modules with their dependencies
- Validate Jev API connectivity with a test call

**Middleware:**

- Request ID middleware (generate UUID per request, attach to logs)
- Timing middleware (measure total request duration)
- Error handling: catch Jev API errors, return 502 with structured error body

**Error responses:**

```python
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str
    timestamp: datetime
```

**Config (`config.py`):**

```python
class Settings(BaseSettings):
    jev_api_key: str
    jev_base_url: str = "https://api.typesafe.ai/v1/"
    mock_jev: bool = False
    quality_threshold_default: int = 70
    route_confidence_minimum: float = 0.5
    notifiable_confidence_minimum: float = 0.8
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")
```

## Test Data

### Synthea Generation

Generate 100 synthetic Indonesian patients using Synthea:

```bash
./run_synthea -p 100 \
  --exporter.fhir.export true \
  --exporter.years_of_history 5 \
  --generate.demographics.default_file demographics_id.csv
```

If Synthea doesn't support Indonesian demographics natively, create a custom demographics CSV with Indonesian names, NIK-format identifiers, and Yogyakarta-area addresses.

### Test Fixtures

Hand-crafted JSON files in `tests/fixtures/`:

**patients/** (20 files):

- `complete_patient.json` — all fields populated, valid NIK
- `missing_identifier.json` — no identifier
- `missing_birthdate.json` — no birthDate
- `invalid_nik.json` — NIK with wrong length (15 digits)
- `minimal_patient.json` — only resourceType + id
- 15 more with varying completeness levels

**conditions/** (15 files):

- `dengue_a90.json` — notifiable, ICD-10 A90
- `je_a83.json` — notifiable, Japanese encephalitis
- `tb_a15.json` — notifiable, tuberculosis
- `common_cold_j06.json` — not notifiable
- `diabetes_e11.json` — not notifiable
- 10 more covering edge cases (ambiguous codes, missing coding system)

**bundles/** (15 files):

- `lab_bundle.json` — Observations with LOINC codes
- `encounter_bundle.json` — Encounter + Conditions
- `immunization_bundle.json` — Immunization resources
- `medication_bundle.json` — MedicationDispense resources
- `mixed_bundle.json` — ambiguous mix of resource types
- 10 more with varying compositions

### Ground Truth

`benchmarks/ground_truth/` contains hand-labeled expected results for each fixture:

```json
{
  "fixture": "patients/complete_patient.json",
  "expected_quality_score_range": [80, 100],
  "expected_nik_valid": true
}
```

## Benchmarking Harness

**Run command:** `make bench` (or `python benchmarks/bench_runner.py`)

**What it does:**

1. Loads all fixtures from `tests/fixtures/`
2. Loads ground truth from `benchmarks/ground_truth/`
3. Runs each fixture through the relevant module (Quality Scorer, Bundle Router, or Notifiable Detector)
4. Runs the same fixtures through rule-based baselines in `benchmarks/baselines/`
5. Compares results and computes metrics
6. Outputs a JSON report + a markdown summary table

**Baselines (`benchmarks/baselines/`):**

- `rule_quality_scorer.py` — counts non-null fields, checks NIK regex
- `rule_bundle_router.py` — checks entry resource types with if/elif
- `rule_notifiable_detector.py` — exact ICD-10 code lookup against the disease list

**Output (`benchmarks/results/`):**

```
results/
├── bench_2026-09-28.json       # Full structured results
├── bench_2026-09-28.md         # Human-readable summary
└── latency_histogram.json      # Per-call latency data
```

**Metrics computed:**

- Accuracy (exact match with ground truth)
- Precision / Recall / F1 (for notifiable disease detection)
- Mean / P50 / P95 latency per module
- Confidence calibration (predicted vs. actual accuracy per confidence bucket)
- Token count and estimated cost
- Jev vs. rule-based comparison table

## Implementation Sequence

Modules have dependencies — build in this order:

**Phase 1: Foundation (Night 1)**

1. Project scaffold — `pyproject.toml`, `Makefile`, `.env.example`, directory structure
2. `config.py` — Settings with pydantic-settings
3. `jev_client/models.py` — Pydantic models for Jev I/O
4. `jev_client/mock.py` — Mock Jev client (enables all development without API access)
5. `jev_client/client.py` — Live Jev client with httpx
6. `logger.py` — Structured decision logger

**Phase 2: Serializers (Night 1–2)** 7. `serializer/base.py` — Abstract serializer interface 8. `serializer/patient.py` + unit tests 9. `serializer/condition.py` + unit tests 10. `serializer/bundle.py` + unit tests 11. `serializer/observation.py` + unit tests

**Phase 3: Decision Modules (Night 2)** 12. `modules/quality_scorer.py` + unit tests (depends on: serializer, jev\_client) 13. `modules/bundle_router.py` + unit tests (depends on: serializer, jev\_client) 14. `modules/notifiable_detector.py` + unit tests (depends on: serializer, jev\_client, fhir\_helpers) 15. `fhir_helpers/flag_builder.py` + unit tests 16. `fhir_helpers/audit_event.py` + unit tests

**Phase 4: API Layer (Night 2–3)** 17. `routes/quality.py` + API tests 18. `routes/routing.py` + API tests 19. `routes/notifiable.py` + API tests 20. `routes/metrics.py` 21. `main.py` — wire everything together

**Phase 5: Benchmark & Polish (Night 3)** 22. Test fixtures — create all FHIR JSON files 23. Ground truth labels 24. Rule-based baselines 25. `bench_runner.py` 26. `data/notifiable_diseases.json` 27. `README.md` with setup, usage, and results

**Dependency graph:**

```
config ──► jev_client ──► modules ──► routes ──► main
                ▲             ▲
           serializers    fhir_helpers
```

## Instructions for AI Coding Agents

This section is for Codex or Claude Code when implementing from this plan.

### For Codex (Implementation)

1. **Start with Phase 1** — scaffold the project exactly as the project structure section describes. Run `pip install -e ".[dev]"` to verify the setup.
2. **Build bottom-up** — follow the implementation sequence strictly. Each module depends on the ones before it. Do not skip ahead.
3. **Write tests alongside code** — every module gets unit tests in the same phase. Use `pytest` with `pytest-asyncio` for async tests. Target ≥ 90% coverage per module.
4. **Use the mock client for development** — set `MOCK_JEV=true` in `.env`. All unit tests must pass with the mock client. Integration tests with the live API are separate.
5. **Match the interfaces exactly** — the Pydantic models and function signatures in this doc are the contract. Don't deviate from the response schemas.
6. **FHIR resources use `fhir.resources`** — import from `fhir.resources.patient import Patient`, etc. Parse incoming JSON with these models for validation before serializing.
7. **Question phrasing** — the exact Jev question strings in each module section are intentional. Store them as module-level constants, not inline strings.
8. **Type everything** — full type hints on all functions. `mypy --strict` must pass.
9. **Makefile commands** — implement: `make lint` (ruff), `make typecheck` (mypy), `make test` (pytest), `make bench` (benchmark harness), `make serve` (uvicorn dev server).

### For Claude Code (Evaluation)

1. **Check project structure** — verify all directories and files exist as specified.
2. **Run `make lint`** — zero ruff errors.
3. **Run `make typecheck`** — zero mypy errors in strict mode.
4. **Run `make test`** — all tests pass with mock client. Check coverage report.
5. **Review serializer output** — verify the serialized output matches the example dicts in Module 1 for representative fixtures.
6. **Review API contracts** — hit each endpoint with a test fixture and verify the response schema matches the PRD's API Contract section.
7. **Spot-check Jev question phrasing** — verify the question constants match what's specified in Modules 3–5.
8. **Review error handling** — send malformed FHIR JSON to each endpoint, verify structured error responses.
9. **If live API access is available** — run `make bench` with `MOCK_JEV=false` and review the benchmark report for accuracy and latency targets from the PRD.
10. **Flag any deviations** from this plan or the PRD — implementation must match spec, not improvise.
