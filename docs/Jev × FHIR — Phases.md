# Jev × FHIR — Phase-by-Phase Implementation Plan

Sep 23, 2026 · @budi

## How to Use This Doc

**Workflow:** Codex builds → Claude Code evaluates → repeat.

Each phase below is a self-contained unit of work. Copy-paste the phase to the relevant agent:

1. Tell Codex: **"Implement Phase 1 of this plan"** (paste the Phase 1 section)
2. When done, tell Claude Code: **"Evaluate Phase 1 of this implementation"** (paste the Phase 1 evaluation checklist)
3. Fix any issues Codex or Claude Code flag
4. Move to Phase 2, repeat

**Rules for both agents:**

- Reference docs: [PRD](https://claude.ai/code/artifact/53377652-7ceb-4f0f-a190-8845760ce95a) and [Technical Spec](https://claude.ai/code/artifact/6d0465ae-279d-4e11-a66d-ee8c7c904d5d) have full module details, API contracts, and Pydantic models
- All tests use the mock Jev client (`MOCK_JEV=true`)
- Each phase must pass its evaluation before moving to the next
- Do not implement anything from a later phase

**Dependency graph:**

```
Phase 1 (foundation) → Phase 2 (serializers) → Phase 3 (decision modules) → Phase 4 (API) → Phase 5 (benchmarks)
```

---

## Phase 1: Foundation

### Codex Instructions

**Goal:** Scaffold the project and build the Jev client layer. After this phase, the project installs, lints, and has a working mock Jev client.

**Step 1 — Project scaffold:**

Create the full directory structure:

```
jev-fhir/
├── README.md                   # placeholder
├── pyproject.toml
├── Makefile
├── .env.example
├── src/jev_fhir/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── jev_client/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── client.py
│   │   └── mock.py
│   ├── serializer/             # empty __init__.py only
│   ├── modules/                # empty __init__.py only
│   ├── fhir_helpers/           # empty __init__.py only
│   └── routes/                 # empty __init__.py only
├── tests/
│   ├── conftest.py
│   ├── fixtures/               # empty dirs: patients/, observations/, conditions/, bundles/
│   └── test_jev_client.py
├── benchmarks/                 # empty dirs: ground_truth/, baselines/, results/
└── data/                       # empty dir
```

`pyproject.toml`:

```toml
[project]
name = "jev-fhir"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "httpx>=0.27.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "fhir.resources>=7.1.0",
    "structlog>=24.4.0",
    "prometheus-client>=0.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
]
```

`Makefile` commands: `make lint` (ruff check + format), `make typecheck` (mypy --strict), `make test` (pytest with coverage), `make bench` (placeholder), `make serve` (uvicorn).

`.env.example`:

```
JEV_API_KEY=your-key-here
JEV_BASE_URL=https://api.typesafe.ai/v1/
MOCK_JEV=true
LOG_LEVEL=INFO
```

**Step 2 — `config.py`:**

```python
class Settings(BaseSettings):
    jev_api_key: str = "mock-key"
    jev_base_url: str = "https://api.typesafe.ai/v1/"
    mock_jev: bool = False
    quality_threshold_default: int = 70
    route_confidence_minimum: float = 0.5
    notifiable_confidence_minimum: float = 0.8
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env")
```

**Step 3 — `jev_client/models.py`:** Pydantic models for `ChoiceResult`, `ScoreResult`, `NoulResult` (see Technical Spec Module 2 for exact fields).

**Step 4 — `jev_client/mock.py`:** `MockJevClient` that implements the `JevClient` ABC. Returns deterministic results based on input hashing. Simulates 10–30ms latency. Confidence values in 0.6–0.95 range.

**Step 5 — `jev_client/client.py`:** `LiveJevClient` using `httpx.AsyncClient`. Bearer token auth, 5s timeout, 2 retries with exponential backoff on 429/5xx. Measure latency with `time.perf_counter()`.

**Step 6 — `logger.py`:** Structured decision logger using `structlog`. Logs every decision as JSON: timestamp, module, resource\_reference, decision, confidence, latency\_ms.

**Step 7 — `tests/test_jev_client.py`:** Test all three primitives (choice, score, noul) against the mock client. Verify response model shapes, latency simulation, and deterministic output.

**Step 8 — Verify:**

```bash
pip install -e ".[dev]"
make lint
make typecheck
make test
```

### Claude Code Evaluation Checklist

Evaluated: Sep 24, 2026

```
✅ Project installs without errors: pip install -e ".[dev]"
✅ All directories exist as specified in the structure above
✅ make lint — zero ruff errors (13 files formatted)
✅ make typecheck — zero mypy errors (strict mode, 13 source files)
✅ make test — all 8 tests pass (0.41s)
✅ config.py loads from .env.example without crashing (test_env_example_loads_without_error)
✅ MockJevClient returns valid ChoiceResult, ScoreResult, NoulResult (3 shape tests)
✅ MockJevClient is deterministic (same input → same output) (test_choice_is_deterministic)
✅ LiveJevClient has retry logic (3 attempts, exponential backoff on 429/5xx) and timeout (5s)
✅ logger.py outputs structured JSON (test_decision_logger_emits_required_json_fields)
✅ No code exists in serializer/, modules/, fhir_helpers/, routes/ (only __init__.py)
✅ test_jev_client.py has 7 test cases covering all three primitives + config + logger
```

**Notes:** Coverage at 78% overall. LiveJevClient at 46% (untested without live API — expected). Mock client at 98%. All other modules ≥ 92%.

**Verdict: Phase 1 PASS — ready for Phase 2.**

---

## Phase 2: FHIR Serializers

**Depends on:** Phase 1 complete and passing.

### Codex Instructions

**Goal:** Build serializers that convert FHIR R4 resources into flat dicts for Jev. After this phase, every serializer has unit tests and produces the exact output shapes specified below.

**Step 1 — `serializer/base.py`:**

```python
class FHIRSerializer(ABC):
    @abstractmethod
    def serialize(self, resource: dict) -> dict[str, Any]: ...
    @abstractmethod
    def resource_type(self) -> str: ...
```

**Step 2 — `serializer/patient.py`:** Serialize Patient resources. Use `fhir.resources.patient.Patient` for parsing. Output:

```python
{
    "resource_type": "Patient",
    "has_identifier": True,
    "identifier_system": "nik",
    "identifier_value_length": 16,
    "has_name": True,
    "name_family": "Wijaya",
    "has_birth_date": True,
    "has_gender": True,
    "has_address": True,
    "address_country": "ID",
    "has_telecom": False,
    "telecom_count": 0,
    "field_completeness": 8,
    "field_total": 10
}
```

Gracefully handle missing fields — set `has_*` to `False`, values to `None`.

**Step 3 — `serializer/condition.py`:** Serialize Condition resources. Output:

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

**Step 4 — `serializer/bundle.py`:** Serialize Bundle resources. Output:

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

**Step 5 — `serializer/observation.py`:** Serialize Observation resources. Extract: code (system + value), status, value (quantity or string), effectiveDateTime, has\_subject, has\_encounter.

**Step 6 — Test fixtures:** Create minimum test fixtures in `tests/fixtures/`:

- `patients/complete_patient.json` — all fields, valid 16-digit NIK
- `patients/minimal_patient.json` — only resourceType + id
- `patients/invalid_nik.json` — NIK with 15 digits
- `conditions/dengue_a90.json` — ICD-10 A90
- `conditions/common_cold_j06.json` — ICD-10 J06.9
- `bundles/lab_bundle.json` — Observations with LOINC codes
- `bundles/mixed_bundle.json` — ambiguous mix

All fixtures must be valid FHIR R4 JSON that passes `fhir.resources` parsing.

**Step 7 — `tests/test_serializer.py`:** Test each serializer against the fixtures above. Verify output shape matches the dicts specified. Test missing-field handling.

**Step 8 — Verify:**

```bash
make lint && make typecheck && make test
```

### Claude Code Evaluation Checklist

Evaluated: Sep 24, 2026

```
✅ make lint — zero errors (19 files, all passed)
✅ make typecheck — zero errors (strict mode, 19 source files)
✅ make test — 21 tests pass (13 new serializer tests), 0.80s
✅ All 4 serializers exist: patient.py, condition.py, bundle.py, observation.py
✅ Each serializer extends FHIRSerializer ABC (base.py defines interface)
✅ PatientSerializer output on complete_patient.json matches specified dict shape (exact equality assert)
✅ PatientSerializer handles missing fields (minimal_patient.json) — all has_* False, values None
✅ ConditionSerializer correctly extracts ICD-10 code system and value (dengue A90 verified)
✅ BundleSerializer correctly identifies dominant_resource_type (Observation for lab bundle)
✅ All 7 test fixtures are valid FHIR R4 (test_all_phase_two_fixtures_are_valid_fhir_r4)
✅ ≥ 3 test cases per serializer (Patient: 3, Condition: 3, Observation: 3, Bundle: 3)
✅ Serializers do NOT call any external API — pure data transformation, fhir.resources validation only
✅ No code exists in modules/ or routes/ beyond __init__.py
```

**Notes:** Coverage up to 87% (from 78%). All 4 serializers at 93-100% coverage. `base.py` helper functions `first_coding_value` lines 41/43 uncovered (edge paths for non-list non-Mapping input). Fixtures include 3 patients, 2 conditions, 2 bundles — spec asked for 7 minimum, met exactly.

**Verdict: Phase 2 PASS — ready for Phase 3.**

---

## Phase 3: Decision Modules

**Depends on:** Phase 2 complete and passing.

### Codex Instructions

**Goal:** Build the three decision modules and FHIR helper utilities. After this phase, each module takes a FHIR resource, calls the mock Jev client, and returns a structured decision.

**Step 1 — `fhir_helpers/flag_builder.py`:** Build FHIR Flag resources for notifiable disease detections.

Input: condition code, condition display, subject reference, detection date. Output: valid FHIR R4 Flag JSON:

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

**Step 2 — `fhir_helpers/audit_event.py`:** Build FHIR AuditEvent resources for decision logging. Input: module name, decision, resource reference, timestamp.

**Step 3 — `data/notifiable_diseases.json`:** Indonesian notifiable disease reference list. Include at minimum:

- A83.0 Japanese encephalitis
- A90, A91 Dengue
- A15–A19 Tuberculosis
- A00 Cholera
- A01 Typhoid
- A30 Leprosy
- B50–B54 Malaria
- B20 HIV

Format:

```json
{"diseases": [{"name": "...", "icd10_codes": ["..."], "category": "...", "reporting_urgency": "24h"}]}
```

**Step 4 — `modules/quality_scorer.py`:**

Jev question constants (store as module-level constants):

```python
QUALITY_SCORE_QUESTION = "Rate the data quality and completeness of this clinical resource from 0 (empty/invalid) to 100 (all fields present, correctly formatted, clinically complete)"
NIK_VALIDATION_STATEMENT = "This patient has a valid 16-digit Indonesian NIK identifier"
```

Flow: accept resource JSON + resource\_type → serialize → call `jev_client.score()` → if Patient, also call `jev_client.noul()` for NIK → apply threshold → return `QualityScoreResponse`.

Response model:

```python
class QualityScoreResponse(BaseModel):
    score: int
    confidence: float
    level: str  # "acceptable" or "review_needed"
    missing_fields: list[str]
    nik_valid: bool | None  # None for non-Patient
    nik_confidence: float | None
    resource_reference: str
    latency_ms: float
    action: str  # "auto_accept" or "review_needed"
```

**Step 5 — `modules/bundle_router.py`:**

Jev question constant:

```python
ROUTE_QUESTION = "What type of clinical data does this FHIR Bundle primarily contain?"
ROUTE_OPTIONS = ["lab_result", "encounter_summary", "immunization_report", "medication_dispense", "unknown"]
```

Flow: accept Bundle JSON → serialize → call `jev_client.choice()` → if confidence < 0.5 override to `unknown` → return `BundleRouteResponse`.

Response model:

```python
class BundleRouteResponse(BaseModel):
    category: str
    confidence: float
    probabilities: dict[str, float]
    bundle_id: str
    latency_ms: float
```

**Step 6 — `modules/notifiable_detector.py`:**

Jev question constant:

```python
NOTIFIABLE_STATEMENT = "This condition is a notifiable disease that requires mandatory reporting to Indonesian public health authorities"
```

Flow: accept Condition JSON → serialize → load disease reference → call `jev_client.noul()` → apply thresholds (≥ 0.8 confirmed, 0.5–0.8 review, < 0.5 not notifiable) → if confirmed, generate Flag via FlagBuilder → return `NotifiableDetectionResponse`.

Response model:

```python
class NotifiableDetectionResponse(BaseModel):
    is_notifiable: bool
    probability: float
    status: str  # "confirmed_notifiable", "review_needed", "not_notifiable"
    condition_code: str
    condition_display: str
    flag_resource: dict | None  # FHIR Flag JSON, only if confirmed
    latency_ms: float
```

**Step 7 — Tests:** Write `test_quality_scorer.py`, `test_bundle_router.py`, `test_notifiable_detector.py`. Use the mock Jev client. Test with Phase 2 fixtures. ≥ 3 tests per module covering: happy path, low-confidence case, missing/malformed input.

**Step 8 — Verify:**

```bash
make lint && make typecheck && make test
```

### Claude Code Evaluation Checklist

Evaluated: Sep 24, 2026

```
✅ make lint — zero errors (25 files, all passed)
✅ make typecheck — zero errors (strict mode, 25 source files)
✅ make test — 32 tests pass (11 new decision module tests), 1.00s
✅ Quality scorer returns QualityScoreResponse shape on complete_patient.json (score=80, action=auto_accept)
✅ Quality scorer calls jev_client.noul() only for Patient resources (StubJevClient.calls verified: Patient→["score","noul"], Observation→["score"])
✅ Bundle router overrides to "unknown" when confidence < 0.5 (test_bundle_router_overrides_low_confidence_choice, confidence=0.49→unknown)
✅ Notifiable detector returns confirmed_notifiable for dengue_a90.json (probability=0.95, flag generated)
✅ Notifiable detector returns not_notifiable for common_cold_j06.json (probability=0.1, no flag)
✅ FlagBuilder output is valid FHIR R4 Flag (Flag.parse_obj in test + builder itself)
✅ Jev question strings match the constants specified above — all 5 constants verified exact match
✅ All three modules accept raw FHIR JSON, not pre-serialized dicts (serialize called internally)
✅ data/notifiable_diseases.json exists with 8 disease entries (JE, Dengue, TB, Cholera, Typhoid, Leprosy, Malaria, HIV)
✅ ≥ 3 test cases per module (QualityScorer: 3, BundleRouter: 3, NotifiableDetector: 3, plus 1 integration + 1 AuditEvent)
✅ No code exists in routes/ beyond __init__.py
```

**Notes:** Coverage up to 91% (from 87%). All 3 decision modules 96-100%. Tests use a StubJevClient with call recording for precise verification, plus one integration test with real MockJevClient. AuditEventBuilder also tested and produces valid FHIR R4. 36 Pydantic deprecation warnings (`parse_obj` → `model_validate`) — cosmetic, from `fhir.resources` library internals, not blocking.

**Verdict: Phase 3 PASS — ready for Phase 4.**

---

## Phase 4: API Layer

**Depends on:** Phase 3 complete and passing.

### Codex Instructions

**Goal:** Wire everything into a FastAPI application with proper endpoints, middleware, and error handling. After this phase, the full API is running and testable via `make serve`.

**Step 1 — `routes/quality.py`:**

`POST /api/v1/quality-score`

Request body:

```python
class QualityScoreRequest(BaseModel):
    resource_type: str
    resource: dict
    threshold: int = 70
```

Response: `QualityScoreResponse` from Phase 3. On error: `ErrorResponse`.

**Step 2 — `routes/routing.py`:**

`POST /api/v1/route-bundle`

Request body:

```python
class BundleRouteRequest(BaseModel):
    bundle: dict
```

Response: `BundleRouteResponse` from Phase 3.

**Step 3 — `routes/notifiable.py`:**

`POST /api/v1/detect-notifiable`

Request body:

```python
class NotifiableDetectRequest(BaseModel):
    condition: dict
```

Response: `NotifiableDetectionResponse` from Phase 3.

**Step 4 — `routes/metrics.py`:**

`GET /api/v1/metrics` — Prometheus-format metrics. Track: request count per endpoint, latency histogram per endpoint, Jev decision count per module, confidence distribution.

**Step 5 — `main.py`:**

```python
app = FastAPI(
    title="Jev × FHIR Decision Layer",
    version="0.1.0",
    description="Proof-of-concept: Jev AI decision primitives for FHIR clinical workflows",
)
```

Startup:

- Load Settings from `.env`
- Initialize JevClient (MockJevClient if `mock_jev=True`, else LiveJevClient)
- Initialize all serializers
- Initialize all modules with dependencies
- Register all routers

Middleware:

- Request ID middleware — generate UUID, attach to logs and response headers
- Timing middleware — measure total request duration, add `X-Request-Duration-Ms` header
- Exception handler — catch `httpx.TimeoutException`, `ValidationError`, return structured `ErrorResponse`

Error response model:

```python
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str
    timestamp: datetime
```

`GET /health` — returns `{"status": "ok", "jev_client": "mock" | "live", "version": "0.1.0"}`

**Step 6 — `tests/test_api.py`:** Integration tests using FastAPI's `TestClient`. Test each endpoint with fixtures from Phase 2. Test error handling with malformed JSON. Verify response schemas match the PRD.

**Step 7 — Verify:**

```bash
make lint && make typecheck && make test
make serve  # manual smoke test: curl the endpoints
```

### Claude Code Evaluation Checklist

Evaluated: Sep 24, 2026

```
✅ make lint — zero errors (33 files, all passed)
✅ make typecheck — zero errors (strict mode, 33 source files)
✅ make test — 41 tests pass (9 new API tests), 1.87s
✅ make serve starts without errors with MOCK_JEV=true (uvicorn smoke tested on :18765)
✅ POST /api/v1/quality-score with complete_patient.json → score=80, action=auto_accept, nik_valid=true
✅ POST /api/v1/route-bundle with lab_bundle.json → category=lab_result, confidence=0.92
✅ POST /api/v1/detect-notifiable with dengue_a90.json → confirmed_notifiable, Flag with SNOMED 281269004
✅ GET /health → {"status":"ok","jev_client":"mock","version":"0.1.0"}
✅ GET /api/v1/metrics → Prometheus text with jev_fhir_http_requests_total, jev_fhir_decisions_total, histograms
✅ Malformed JSON → 422 with {error, detail, request_id, timestamp} — request_id matches X-Request-Id header
✅ Invalid resource_type (Condition to quality-score) → 400 invalid_request, not crash
✅ Response headers include X-Request-Id and X-Request-Duration-Ms (verified in test + smoke test)
✅ All route files use dependency injection via Depends(get_*) — no global state, AppServices dataclass on app.state
✅ test_api.py has ≥ 2 tests per endpoint: quality(2), route(2), notifiable(2), health(1), metrics(1), malformed(1) = 9 total
```

**Notes:** Coverage up to 93% (from 91%). All routes 100%. main.py at 93% — uncovered lines are LiveJevClient init path (mock-only tests) and three exception handlers (httpx.TimeoutException, JevClientError, PydanticV1ValidationError) not triggered in test suite. Clean dependency injection via `dependencies.py` with `AppServices` frozen dataclass — modules injected per-request, no module-level mutable state. Prometheus metrics module tracks HTTP requests, latency, Jev decisions, and confidence distributions. `make serve` now wired to `uvicorn jev_fhir.main:app`.

**Verdict: Phase 4 PASS — ready for Phase 5.**

---

## Phase 5: Test Data & Benchmarks

**Depends on:** Phase 4 complete and passing.

### Codex Instructions

**Goal:** Expand test data, build rule-based baselines, and create the benchmark harness. After this phase, `make bench` produces a comparison report and the project has a complete README.

**Step 1 — Expand test fixtures:**

Add more fixtures to `tests/fixtures/` (target: 20 patients, 15 conditions, 15 bundles):

**patients/** — add 15 more with varying completeness: missing address, missing gender, multiple identifiers, non-Indonesian patient, empty telecom array, etc.

**conditions/** — add 10 more: TB (A15), cholera (A00), malaria (B50), HIV (B20), leprosy (A30), plus non-notifiable: hypertension (I10), asthma (J45), fracture (S72), plus edge cases: missing coding system, no ICD-10 code (SNOMED only).

**bundles/** — add 10 more: medication\_bundle, encounter\_bundle, immunization\_bundle, plus bundles with 1 entry, 50 entries, empty entries, nested bundles.

All fixtures must be valid FHIR R4.

**Step 2 — `benchmarks/ground_truth/`:** Hand-label expected results for every fixture:

```json
// ground_truth/quality_scores.json
[
  {"fixture": "patients/complete_patient.json", "expected_score_range": [80, 100], "expected_nik_valid": true},
  {"fixture": "patients/minimal_patient.json", "expected_score_range": [0, 30], "expected_nik_valid": null}
]

// ground_truth/bundle_routes.json
[
  {"fixture": "bundles/lab_bundle.json", "expected_category": "lab_result"},
  {"fixture": "bundles/mixed_bundle.json", "expected_category": "unknown"}
]

// ground_truth/notifiable_diseases.json
[
  {"fixture": "conditions/dengue_a90.json", "expected_notifiable": true},
  {"fixture": "conditions/common_cold_j06.json", "expected_notifiable": false}
]
```

**Step 3 — `benchmarks/baselines/`:** Rule-based comparison implementations:

`rule_quality_scorer.py` — count non-null fields / total expected fields × 100. NIK: regex check for exactly 16 digits.

`rule_bundle_router.py` — if/elif on entry resource types: > 50% Observation with LOINC → lab\_result, has Encounter → encounter\_summary, has Immunization → immunization\_report, has MedicationDispense → medication\_dispense, else unknown.

`rule_notifiable_detector.py` — exact ICD-10 code lookup against `data/notifiable_diseases.json`. Exact match → notifiable, no match → not.

**Step 4 — `benchmarks/bench_runner.py`:**

Run command: `make bench` (or `python benchmarks/bench_runner.py`)

Flow:

1. Load all fixtures and ground truth
2. Run each fixture through the Jev-based module
3. Run each fixture through the rule-based baseline
4. Compare both against ground truth
5. Compute metrics:
   - Accuracy (exact match with ground truth)
   - Precision / Recall / F1 (notifiable detection)
   - Mean / P50 / P95 latency per module
   - Confidence calibration (predicted vs. actual per bucket)
   - Token count and estimated cost
6. Output:
   - `benchmarks/results/bench_<date>.json` — full structured results
   - `benchmarks/results/bench_<date>.md` — markdown summary table
   - Print summary to stdout

**Step 5 — `README.md`:** Complete project README with:

- Project description (one paragraph)
- Architecture diagram (ASCII art from the idea exploration doc)
- Quick start: clone, `.env`, install, `make serve`
- API reference: all endpoints with example curl commands
- Running benchmarks: `make bench`
- Project structure overview
- Tech stack
- License: MIT

**Step 6 — Verify:**

```bash
make lint && make typecheck && make test
make bench  # with MOCK_JEV=true
```

### Claude Code Evaluation Checklist

Evaluated: Sep 24, 2026

```
✅ make lint — zero errors (42 files, all passed)
✅ make typecheck — zero errors (strict mode, 40 source files)
✅ make test — 43 tests pass (all phases), 3.49s
✅ make bench — runs to completion, produces .json + .md output files
✅ benchmarks/results/ contains timestamped .json and .md output files
✅ Benchmark report includes Jev vs. rule-based comparison table (3 modules × 2 approaches)
✅ Benchmark report includes latency metrics (mean, p50, p95) per module
✅ 20 patient fixtures, 15 condition fixtures, 15 bundle fixtures — exact targets
✅ Every fixture has a ground truth label (20 + 15 + 15 = 50 labels)
✅ Rule-based baselines produce results for all fixtures (all 50 run in bench)
✅ README.md exists with: description, architecture diagram, quick start, API reference (5 curl examples), benchmarks, project structure, tech stack, MIT license
⚠️ README curl for detect-notifiable returns 422 — missing clinicalStatus + subject fields required by fhir.resources Condition validation. Other 4 curl examples work. Error is handled gracefully (structured 422, not crash).
✅ All Makefile commands work: lint, typecheck, test, bench, serve
✅ Final coverage report: 93% overall (exceeds 80% target)
✅ No hardcoded API keys or secrets — only "mock-key" default and config reads from env
```

**Benchmark Results (mock Jev):**

| Module | Fixtures | Jev accuracy | Rule accuracy | Mean ms | P50 ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| quality_scorer | 20 | 1.000 | 1.000 | 43.1 | 44.7 | 53.1 |
| bundle_router | 15 | 0.733 | 0.933 | 27.5 | 28.4 | 40.6 |
| notifiable_detector | 15 | 1.000 | 1.000 | 20.7 | 19.7 | 29.8 |

Notifiable disease detection: Jev and Rule both achieve precision=1.0, recall=1.0, F1=1.0 on mock data.

**Issue to fix:** README curl example for `/api/v1/detect-notifiable` needs `clinicalStatus` and `subject` fields to produce a 200. Low severity — cosmetic README fix, not a code bug.

**Verdict: Phase 5 PASS (with one minor README curl fix needed).**
