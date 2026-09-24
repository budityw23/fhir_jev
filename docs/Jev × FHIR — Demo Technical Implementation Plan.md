# Jev × FHIR — Demo Technical Implementation Plan (Phase by Phase)

Sep 24, 2026 · @budi

## How to Use This Doc

**Workflow:** Codex implements → Codex evaluates → fix → repeat.

Each phase below is a self-contained unit of work with two parts:

1. **Codex Implementation**: tell Codex *"Implement Phase Dx of the Demo Technical Implementation Plan"* and paste that phase's implementation section.
2. **Codex Evaluation**: in a **fresh Codex session** (not the one that wrote the code), tell Codex *"Evaluate Phase Dx"* and paste that phase's evaluation checklist. Codex runs every command, ticks each item with evidence, and fills in the **Evaluation Record** at the end of the phase.
3. Fix anything the evaluation flags, re-run the evaluation, then move on.

Using a fresh session for evaluation matters: the session that wrote the code tends to grade its own assumptions as correct.

**Reference docs:**

- [Demo Plan & UI Requirements](Jev%20×%20FHIR%20—%20Demo%20Plan%20Requirement.md): *what* to build and why (scenario, screens, requirement IDs such as `UI-S-3`, `DEMO-API-4`, findings `F1`–`F11`)
- [Phases](Jev%20×%20FHIR%20—%20Phases.md): the Phase 1–5 build this extends (same workflow)
- [Technical Implementation Plan](Jev%20×%20FHIR%20—%20Technical%20Implementation%20Plan.md): original module contracts
- [PRD](Jev%20×%20FHIR%20—%20PRD.md): targets the benchmarks are judged against

**Rules for every phase:**

- **Tests use the mock client only.** `make test` must never call the live Jev API. Live steps are marked **(manual, Budi)**.
- **Do not change Phase 4 contracts.** `POST /api/v1/quality-score`, `/route-bundle`, `/detect-notifiable` keep their response models. Additive request fields are allowed only where a step says so.
- **Quality bar (backend):** `make lint`, `make typecheck` (mypy `--strict`) and `make test` green; coverage ≥ 95%.
- **Quality bar (frontend, D2+):** `npm run lint`, `npm run typecheck`, `npm run test` and `npm run e2e` green.
- **Interfaces in this doc are the contract.** Names, fields and signatures must match. If something can't work as written, stop and record why in the Evaluation Record rather than improvising.
- **Labels are never computed from the logic under test** (not `field_completeness`, not the rule baselines, not `MockJevClient`).
- **Do not implement anything from a later phase.**
- Match existing style: module docstrings, `from __future__ import annotations` only where already used, Pydantic v2, `structlog`, `Depends(...)` injection through `AppServices`.

**Dependency graph:**

```
D0 (live readiness) → D0.5 (benchmark dataset) → D1 (demo API) → D2 (UI shell + Studio) → D3 (Live Pipeline) → D4 (Benchmarks, presenter, rehearsal)
```

**Final layout after D4** (new or changed paths only):

```
.gitignore                        # web/node_modules, web/dist already added
Makefile                          # new targets per phase
scripts/
├── smoke_live.py                 # D0
├── generate_dataset.py           # D0.5
└── dump_openapi.py               # D2
src/jev_fhir/
├── config.py                     # D0 new settings
├── dependencies.py               # D0/D1 AppServices grows
├── main.py                       # D0 error mapping, /health; D1 demo mount, static, CORS
├── jev_client/client.py          # D0 SDK config + typed errors
├── jev_client/recording.py       # D0 RecordingJevClient
├── baselines/                    # D0 moved from benchmarks/baselines
├── dataset/labels.py             # D0 label models + loader
├── fhir_helpers/                 # D0 R4B + R4-shaped AuditEvent
├── demo/                         # D1
│   ├── schemas.py · catalog.py · compare.py · lanes.py · feed.py · pipeline.py · static.py
└── routes/demo.py                # D1
benchmarks/
├── bench_runner.py               # D0 --live/--limit; D0.5 --dataset
└── dataset/
    ├── hard/ · generated/ · demo/
    └── labels/ quality.json · bundle_routes.json · notifiable.json
tests/
├── fixtures/observations/        # D0.5 (10 files)
├── test_live_readiness.py        # D0
├── test_dataset.py               # D0.5
├── test_demo_*.py                # D1
web/                              # D2–D4
```

---

## Phase D0: Live Readiness & Cleanup

**Depends on:** Phases 1–5 complete (they are).
**Requirement refs:** Demo Plan §1.3 findings F1–F9, F11; DEMO-BE-1, DEMO-BE-10.

### Codex Implementation

**Goal:** make live Jev results trustworthy and debuggable before any UI exists. After this phase, the live client is configurable and fails loudly with typed errors, the benchmark can run live, quality labels are banded, and FHIR validation targets R4.

**Already done (Sep 24): don't redo.** README rewritten; `.env.example` holds a placeholder and the real key is in the git-ignored `.env`; `.gitignore` covers `web/node_modules/` and `web/dist/`.

**Step 1 — Settings (`config.py`):** add the fields below and keep the existing ones. `PROJECT_ROOT` makes default paths independent of the working directory.

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # existing
    jev_api_key: str = "mock-key"
    jev_base_url: str = "https://api.typesafe.ai"
    mock_jev: bool = False
    quality_threshold_default: int = 70
    route_confidence_minimum: float = 0.5
    notifiable_confidence_minimum: float = 0.8          # "confirmed" threshold
    log_level: str = "INFO"
    # new in D0
    notifiable_review_minimum: float = 0.5
    jev_model: str = "jev-latest"
    jev_timeout_s: float = 5.0
    jev_max_retries: int = 2
    jev_retry_budget_s: float = 12.0
    labels_dir: Path = PROJECT_ROOT / "benchmarks" / "dataset" / "labels"
```

Add `JEV_MODEL=jev-latest` to `.env.example`.

**Step 2 — Typed Jev errors (`jev_client/client.py`):**

```python
class JevClientError(RuntimeError):
    """Base error; maps to 502 jev_error."""
    error_code: ClassVar[str] = "jev_error"
    status_code: ClassVar[int] = 502

class JevTimeoutError(JevClientError):
    error_code = "jev_timeout"; status_code = 504

class JevRateLimitError(JevClientError):
    error_code = "jev_rate_limited"; status_code = 429

class JevAuthError(JevClientError):
    error_code = "jev_auth"; status_code = 502
```

In `LiveJevClient._system_one`, map SDK errors **in this order**. `TypeSafeAPITimeoutError` is a subclass of `TypeSafeAPIConnectionError`, so it must be caught first:

| SDK exception | Raise |
| --- | --- |
| `TypeSafeAPITimeoutError` | `JevTimeoutError` |
| `TypeSafeRateLimitError` | `JevRateLimitError` |
| `TypeSafeAuthenticationError`, `TypeSafePermissionDeniedError` | `JevAuthError` |
| any other `TypeSafeError` | `JevClientError(f"Jev SDK request failed: {type(error).__name__}")` |

Always `raise ... from error`. Message format for all of them: `"Jev SDK request failed: <SDK class name>"`. This keeps `test_live_client_wraps_sdk_errors` passing.

**Step 3 — SDK configuration (`LiveJevClient.__init__`):**

```python
def __init__(
    self,
    api_key: str,
    base_url: str,
    *,
    model: str = "jev-latest",
    timeout_s: float = 5.0,
    max_retries: int = 2,
    retry_budget_s: float = 12.0,
    client: AsyncTypeSafeClient | None = None,
) -> None:
```

When `client is None`, build `AsyncTypeSafeClient(api_key=..., base_url=self._sdk_base_url(base_url), model=model, timeout=timeout_s, retry=RetryPolicy(max_retries=max_retries, timeout=retry_budget_s))`. Remove the `_MODEL` class constant; store `self.model = model`.

**Step 4 — `main.py`:**
- Build `LiveJevClient` from all Settings fields in Step 1.
- Replace the single `JevClientError` handler with one that uses `exc.status_code` and `exc.error_code`, with `detail=str(exc)`.
- `/health` returns `{"status", "jev_client", "jev_model", "version"}`. `jev_model` is `settings.jev_model` in live mode and `None` in mock mode.
- `AppServices` gains `settings: Settings`, `jev_client: JevClient` and `jev_model: str | None`, keeping the existing fields.

**Step 5 — Thresholds from Settings (F7):**
- `QualityScoreRequest.threshold` becomes `int | None = Field(default=None, ge=0, le=100)`. The route uses `body.threshold if body.threshold is not None else settings.quality_threshold_default`. The response model is unchanged.
- The `route-bundle` route calls `bundle_router.route(body.bundle, confidence_minimum=settings.route_confidence_minimum)`.
- The `detect-notifiable` route calls `detector.detect(body.condition, confirmed_threshold=settings.notifiable_confidence_minimum, review_threshold=settings.notifiable_review_minimum)`.
- Add a `get_settings_dep(request) -> Settings` provider in `dependencies.py` that reads `AppServices.settings`.

**Step 6 — Noul probability convention (F3):**
- `NoulResult.probability` docstring: *"Probability that the statement is true (P(true)), in [0, 1]."*
- `MockJevClient.noul`, NIK path: `probability = 0.94 if answer else 0.08` (was `0.92` for false).
- `QualityScoreResponse.nik_confidence` keeps its name. Add a field docstring saying it holds P(NIK valid).

**Step 7 — `RecordingJevClient` (`jev_client/recording.py`, DEMO-BE-10):**

```python
class JevCall(BaseModel):
    """One primitive call and its raw typed result."""
    primitive: Literal["choice", "score", "noul"]
    question: str
    options: list[str] | None = None
    result: ChoiceResult | ScoreResult | NoulResult


class RecordingJevClient(JevClient):
    """Forward to an inner client and keep every raw result.

    Not shared across concurrent requests: create one per request or per benchmark item.
    """

    def __init__(self, inner: JevClient) -> None: ...
    @property
    def calls(self) -> list[JevCall]: ...
    @property
    def total_tokens(self) -> int: ...
    def drain(self) -> list[JevCall]:
        """Return recorded calls and clear the buffer."""
```

Export it from `jev_client/__init__.py`.

**Step 8 — Baselines into the package (DEMO-BE-1):** move `benchmarks/baselines/*.py` to `src/jev_fhir/baselines/`:

```
src/jev_fhir/baselines/__init__.py
src/jev_fhir/baselines/quality.py          # score_patient(resource) -> dict (same as today)
src/jev_fhir/baselines/bundle_router.py    # route_bundle(bundle) -> str, route_options()
src/jev_fhir/baselines/notifiable.py       # is_notifiable(condition, disease_data_path) -> bool
```

Delete `benchmarks/baselines/` and update `bench_runner.py` and `tests/test_benchmarks.py` imports. Keep the logic byte-for-byte except imports.

**Step 9 — FHIR R4 validation (F11): ✅ Done Sep 24, 2026 (don't redo; verify only).**
- All imports in `src/` and `tests/` now use `fhir.resources.R4B.*`. `fhir.resources` 8.x defaults to R5, and no release that works with Pydantic v2 ships plain R4 (4.0.1): the 6.x line needs Pydantic v1 and is itself R4B. R4B matches R4 for every resource used here, and that was confirmed against the official HL7 R4 4.0.1 JSON schema.
- `AuditEventBuilder` emits the R4 shape: `type` as a Coding, and `entity.detail.type` as a string. The R5-only `code` field is gone.
- Three R5-only fixtures were fixed: `bundles/encounter_bundle.json` (added the required `class`; `status` changed from `completed` to `finished`), `bundles/medication_bundle.json` and `bundles/medication_and_condition_bundle.json` (`medication.concept` changed to `medicationCodeableConcept`). Mock benchmark accuracy is unchanged.
- New regression tests: `test_every_fixture_is_valid_fhir_r4` (parametrised over all fixtures) and R4-shape assertions in `test_audit_event_builder_returns_valid_fhir_resource`.
- README: `clinicalStatus` is optional in R4, so the notifiable endpoint accepts a Condition without it (verified 200); `subject` is still required (verified 422).
- **Carry forward:** every new fixture in D0.5 (Observations, hard cases, generated, demo) must use R4 structures. Watch for R5 habits: `Encounter.class` is a single Coding and required; `Encounter.status` uses `finished`, not `completed`; MedicationDispense uses `medicationCodeableConcept` / `medicationReference`; AuditEvent uses `type`.

**Step 10 — Label models and banded quality labels (F1):** create `src/jev_fhir/dataset/labels.py`. D0 uses only `QualityLabel`; D0.5 adds the other two.

```python
Source = Literal["unit", "hard", "generated", "demo"]
Difficulty = Literal["easy", "hard"]


class LabelBase(BaseModel):
    fixture: str                   # POSIX path relative to PROJECT_ROOT
    source: Source
    difficulty: Difficulty
    rationale: str = Field(min_length=10)
    approved_by: str | None = None # "budi" once reviewed


class QualityLabel(LabelBase):
    resource_type: Literal["Patient", "Observation"]
    expected_action: Literal["auto_accept", "review_needed"]   # at threshold 70
    expected_score_range: tuple[int, int]                       # width >= 20
    expected_nik_valid: bool | None = None

    @model_validator(mode="after")
    def _banded(self) -> "QualityLabel": ...  # 0<=lo<hi<=100 and hi-lo >= 20


def load_labels(path: Path, model: type[L]) -> list[L]: ...
def fixture_path(label: LabelBase) -> Path: ...  # PROJECT_ROOT / label.fixture, must stay inside PROJECT_ROOT
```

- Create `benchmarks/dataset/labels/quality.json` (a JSON array of `QualityLabel`) for the 20 unit patients, with `fixture` paths like `tests/fixtures/patients/complete_patient.json`, `source: "unit"` and `approved_by: null`.
- Write each `rationale` from reading the fixture (e.g. *"All demographics present, valid 16-digit NIK, no telecom → usable, auto-accept"*).
- Delete `benchmarks/ground_truth/quality_scores.json`.

**Step 10b — NIK gate and label consistency (added after the D0 review, done Sep 24, 2026):**
- `QualityScorer` auto-accepts a Patient only when `score >= threshold` **and** `nik_valid is not False` (Budi's decision: the NIK check is a gate, not just information). The rule baseline in the benchmark applies the same gate.
- `QualityLabel` has a second validator: `auto_accept` needs a band entirely ≥ 70 and a NIK that isn't expected to be invalid; `review_needed` with a passing NIK needs a band entirely < 70. `review_needed` with a failing NIK may have a high band.
- Relabelled 11 unit labels: 7 band fixes, plus `full_no_nik`, `invalid_nik`, `short_identifier` and `non_indonesian` moved to `review_needed`.
- **Carry forward to D0.5:** generated and hard quality labels must pass this validator. Any Patient with a failing NIK is `review_needed`.

**Step 11 — Benchmark runner goes live (F2):**
- CLI: `--live` (use `LiveJevClient` from Settings; default mock), `--limit N` (first N items per module, for cheap runs), `--output-dir`.
- Wrap the client in `RecordingJevClient`; call `drain()` after each item to attach `tokens_used` and `jev_latency_ms` to the row.
- Quality now reads `labels/quality.json`:
  - `jev_accuracy` is **action agreement** (the `action` at threshold 70 equals `expected_action`).
  - A new `jev_score_in_band` metric reports the score-in-band rate.
  - Rule baseline action is `rule score >= 70`, with the same two metrics.
- Report top-level fields:

```json
{
  "generated_at": "...",
  "mode": "mock_jev | live_jev",
  "jev_model": "jev-latest | null",
  "dataset": "unit",
  "quality_labels_banded": true,
  "token_and_cost": {"tokens_used": 0, "estimated_cost_usd": 0.0,
                     "pricing_note": "total tokens × $42 / 1e9 (upper bound: PRD prices input tokens)"},
  "modules": {"...": "as today, rows gain tokens_used, jev_latency_ms, jev_confidence"}
}
```

- Makefile: `bench` stays mock and offline; add `bench-live: MOCK_JEV=false python -m benchmarks.bench_runner --live`.

**Step 12 — Live smoke script (`scripts/smoke_live.py`, `make smoke-live`):**
- Refuses to run (exit 2 with a message) if `jev_api_key` is `mock-key` or `your-key-here`.
- Runs one call per module on `tests/fixtures/patients/complete_patient.json`, `tests/fixtures/bundles/lab_bundle.json` and `tests/fixtures/conditions/japanese_encephalitis_a83.json`.
- Prints a table: module, decision, confidence/probability, Jev latency ms, tokens.
- Exits 1 on any `JevClientError`, printing `error_code`.
- Makefile: `smoke-live: MOCK_JEV=false python scripts/smoke_live.py`.

**Step 13 — Tests (`tests/test_live_readiness.py`, plus updates to existing files):**
- `LiveJevClient` passes `model`, `timeout` and a `RetryPolicy` with the configured values (patch `AsyncTypeSafeClient` and assert kwargs).
- Four SDK error types map to four error classes; the timeout-before-connection ordering has its own test.
- API: an injected client that raises each error type → the correct HTTP status and `error` code.
- `/health` includes `jev_model` (`None` in mock).
- Mock NIK invalid → `probability < 0.5`; valid → `> 0.5`.
- `RecordingJevClient` records all three primitives, sums tokens, and `drain()` clears.
- Route defaults come from Settings: a `Settings(quality_threshold_default=90)` app turns `complete_patient` into `review_needed`.
- `QualityLabel` rejects a single-point range and a width < 20.
- `AuditEventBuilder` output parses with `fhir.resources.R4B.auditevent.AuditEvent`.
- The bench runner `--limit 2` (mock) writes a report with `mode == "mock_jev"` and `quality_labels_banded is True`.

**Step 14 — Verify:**

```bash
make lint && make typecheck && make test && make bench
```

**Step 15 — Manual (Budi):** rotate the old key in the TypeSafe dashboard and update `.env`, then run `make smoke-live` and `make bench-live`, and commit the live report.

### Codex Evaluation Checklist

Run every command. Paste short evidence (a number or output line) next to each item.

```
✅ make lint → "All checks passed"; "48 files already formatted"
✅ make typecheck → "Success: no issues found in 44 source files"
✅ make test → 114 passed; coverage TOTAL = 96%
✅ make bench → report written; mode=mock_jev, dataset=unit, quality_labels_banded=true, jev_model=null
✅ Bundle router 0.733, notifiable 1.000 — unchanged from pre-D0 report
✅ grep -rn "_MODEL\b" src/ → no matches; main.py:61-68 passes model/timeout_s/max_retries/retry_budget_s from Settings to LiveJevClient
✅ client.py error order: line 190 TypeSafeAPITimeoutError → 192 TypeSafeRateLimitError → 196 TypeSafeAPIConnectionError → 198 TypeSafeError
✅ 4 error-mapping API tests: test_api_maps_typed_jev_errors[timeout-504], [rate_limit-429], [auth-502], [other-502] (test_live_readiness.py:146)
   4 SDK-mapping tests: test_live_client_maps_sdk_errors[Timeout→JevTimeoutError], [RateLimit→JevRateLimitError], [Auth→JevAuthError], [Connection→JevClientError] (test_live_readiness.py:45)
✅ curl /health → {"status":"ok","jev_client":"mock","jev_model":null,"version":"0.1.0"}
✅ Mock NIK: invalid → answer=False, prob=0.08 (< 0.5); valid → answer=True, prob=0.94 (> 0.5). Test: test_mock_nik_probability_is_probability_true (line 95)
✅ recording.py exists; RecordingJevClient + JevCall exported from jev_client/__init__.py (lines 13, 26)
⚠️ benchmarks/baselines/ directory still exists (empty after move); src/jev_fhir/baselines/ has __init__.py, bundle_router.py, notifiable.py, quality.py
✅ grep -rn "from fhir.resources\.[a-z]" src tests → no matches (all imports use fhir.resources.R4B.*) (done Sep 24)
✅ AuditEvent built by AuditEventBuilder has "type" and no "code" key (done Sep 24; asserted in test)
✅ All existing fixtures validate under R4B (done Sep 24; 3 bundles fixed, see Step 9)
✅ labels/quality.json: 20 entries; 0 with width < 20; 0 with rationale < 10 chars; all approved_by = null
✅ benchmarks/ground_truth/quality_scores.json deleted (bundle_routes.json + notifiable_diseases.json remain for D0.5 migration)
✅ Threshold settings used outside config.py: routes/quality.py:31 (quality_threshold_default), routes/routing.py:30 (route_confidence_minimum), routes/notifiable.py:34-35 (notifiable_confidence_minimum, notifiable_review_minimum)
✅ smoke-live with JEV_API_KEY=mock-key → "Live smoke requires a real JEV_API_KEY in .env; no network call was made." exit 2. Same for "your-key-here".
✅ detect-notifiable curl returns 200 with confirmed_notifiable (tested with JE A83.0 condition)
✅ No test makes real network calls: all LiveJevClient( usages inject mock via client= param (line 51) or patch constructor (line 62)
☐ (manual, Budi) old key rotated; make smoke-live succeeds; live report committed with mode=live_jev, tokens_used > 0
```

### Evaluation Record

```
Evaluated: Sep 24, 2026 by Claude Code (Opus 4.6)
Results:   18/19 automated checks ✅, 1 ⚠️ (minor), 1 manual pending
Fixtures changed for R4B: none (done Sep 24 pre-D0)
Issues:
  ⚠️ benchmarks/baselines/ directory still exists (empty). Spec says "Delete benchmarks/baselines/".
     The .py files were moved correctly to src/jev_fhir/baselines/ and imports updated.
     The empty directory should be removed (rmdir benchmarks/baselines).
     Non-blocking: no code references it, make bench works.
  ℹ️ 106 Pydantic deprecation warnings (parse_obj → model_validate) from fhir.resources library.
     Pre-existing, cosmetic, not introduced by D0. Non-blocking.
  ℹ️ Live smoke (with real key in .env) ran successfully: quality 1229ms, router 291ms, notifiable 316ms.
     All three modules returned valid decisions. This verifies the live client works.
Verdict:   PASS (pending Budi's manual items: key rotation, label review, live bench report)
```

---

## Phase D0.5: Benchmark Dataset

**Depends on:** D0 PASS.
**Requirement refs:** Demo Plan F10, Phase D0.5 in the Demo Plan, Open Questions 8–10.

### Codex Implementation

**Goal:** a dataset that reaches the PRD's evaluation sizes, contains cases where exact-code rules and field counting *should* fail, and supplies realistic demo presets. The 50 unit fixtures and `make test` stay small and fast.

**Step 1 — Remaining label models (`dataset/labels.py`):**

```python
RouteCategory = Literal["lab_result", "encounter_summary", "immunization_report",
                        "medication_dispense", "unknown"]


class RouteLabel(LabelBase):
    expected_category: RouteCategory


class NotifiableLabel(LabelBase):
    expected_status: Literal["confirmed_notifiable", "review_needed", "not_notifiable"]

    @property
    def expected_notifiable(self) -> bool:
        return self.expected_status == "confirmed_notifiable"
```

Migrate `benchmarks/ground_truth/bundle_routes.json` → `labels/bundle_routes.json` and `notifiable_diseases.json` → `labels/notifiable.json` in the new schema (`source: "unit"`, root-relative `fixture`, `rationale`). Delete `benchmarks/ground_truth/`.

**Step 2 — Observation fixtures (`tests/fixtures/observations/`, 10 files, all valid R4B):**

| File | Content | Draft label |
| --- | --- | --- |
| `complete_lab_hb.json` | LOINC 718-7, `valueQuantity` 13.5 g/dL, subject, encounter, `effectiveDateTime`, `status: final` | auto_accept, 70–100 |
| `vital_heart_rate.json` | LOINC 8867-4, 72 /min, complete | auto_accept, 70–100 |
| `missing_value.json` | complete but no `value[x]` | review, 30–70 |
| `missing_code_system.json` | `code.coding[0]` has code, no system | review, 30–70 |
| `entered_in_error.json` | complete, `status: entered-in-error` | review, 0–50 |
| `value_string.json` | LOINC 718-7 with `valueString: "normal"` | review, 30–70 |
| `no_subject.json` | complete but no subject | review, 20–60 |
| `unusual_unit.json` | 718-7 in `mmol/L` (8.4) | auto_accept, 60–100 |
| `future_effective.json` | `effectiveDateTime` 2030-01-01 | review, 20–70 |
| `local_code_only.json` | only a local code system, no LOINC | review, 30–70 |

Add them to `labels/quality.json` (`resource_type: "Observation"`, `source: "unit"`). Add `score_observation(resource) -> dict` to `baselines/quality.py`: present-field count over `code`, `code.system`, `value`, `status == final|amended`, `subject`, `encounter`, `effective` → 0–100. The bench runner runs Observations through `QualityScorer` too.

**Step 3 — Hard cases (`benchmarks/dataset/hard/`, ≥ 25 files, all valid R4B):**

```
hard/conditions/
  tb_subcode_a15_0.json            A15.0                         → confirmed_notifiable
  malaria_subcode_b50_9.json       B50.9                         → confirmed_notifiable
  typhoid_subcode_a01_0.json       A01.0                         → confirmed_notifiable
  dengue_hemorrhagic_a91.json      A91 "Dengue haemorrhagic fever" → confirmed_notifiable
  dengue_snomed_only.json          SNOMED 38362002 only          → confirmed_notifiable
  tb_snomed_only.json              SNOMED 56717001 only          → confirmed_notifiable
  dbd_text_only.json               code.text "Demam berdarah dengue (DBD)", no coding → confirmed_notifiable
  tb_paru_text_only.json           code.text "TB paru", no coding → confirmed_notifiable
  dengue_refuted.json              A90, verificationStatus refuted       → not_notifiable
  cholera_entered_in_error.json    A00, verificationStatus entered-in-error → not_notifiable
  code_display_mismatch.json       J06.9 with display "Dengue fever"     → review_needed
  fever_unspecified_r50_9.json     R50.9                                 → review_needed
  viral_infection_b34_9.json       B34.9                                 → not_notifiable
  pneumonia_j18_9.json             J18.9                                 → not_notifiable
hard/patients/
  nik_dotted.json                  "3173.0101.0190.0001"   → review_needed, nik_valid true
  nik_spaced.json                  "3173 0101 0190 0001"   → review_needed, nik_valid true
  nik_letters.json                 16 chars incl. letters  → review_needed, nik_valid false
  nik_all_zeros.json               "0000000000000000"      → review_needed, nik_valid false
  nik_wrong_system.json            valid 16 digits under a passport system URL → review_needed, nik_valid false
  placeholder_name.json            name.family "-", given ["unknown"] → review_needed
  placeholder_address.json         address.text "." only   → review_needed
  future_birthdate.json            birthDate 2031-05-01    → review_needed
  ancient_birthdate.json           birthDate 1850-01-01    → review_needed
hard/bundles/
  realistic_lab_submission.json    Patient+Encounter+DiagnosticReport+6 lab Observations → lab_result
  immunization_with_context.json   Patient+Encounter+Practitioner+2 Immunization          → immunization_report
  medication_transaction.json      type transaction, request entries, MedicationDispense   → medication_dispense
  vitals_only.json                 4 vital-sign Observations (no lab LOINC)               → (Open Question 10; draft unknown)
  genuinely_mixed.json             3 labs + 2 immunizations + 1 dispense                   → unknown
```

- Every hard label has `source: "hard"`, `difficulty: "hard"`, a rationale that explains *why rules should struggle*, and `approved_by: null`.
- Don't use ICD-10 A02–A09 anywhere until Open Question 9 is answered.

**Step 4 — Generator (`scripts/generate_dataset.py`, `make dataset`):**
- CLI: `--seed 42` (default), `--out benchmarks/dataset/generated`, `--check` (regenerate to a temp dir and exit 1 if anything differs from the committed files).
- Determinism: one `random.Random(seed)`; no `datetime.now()`, `uuid4()` or set iteration. Write JSON with `indent=2, sort_keys=True`, UTF-8 and a trailing newline, so two runs are byte-identical.
- **Bundles: 80 generated**, bringing the total to 102 (15 unit + 5 hard + 80 generated + 2 demo). Templates by construction:

| Template | Count | Content | Label |
| --- | ---: | --- | --- |
| lab | 18 | 1–30 lab Observations from a LOINC pool (718-7, 789-8, 2345-7, 4548-4, 2160-0, NS1 dengue antigen); optionally Patient/Encounter/DiagnosticReport | `lab_result` |
| encounter | 18 | Encounter + 1–4 Conditions (+ Practitioner optional) | `encounter_summary` |
| immunization | 16 | 1–5 Immunizations (+ Patient optional) | `immunization_report` |
| medication | 16 | 1–5 MedicationDispense (+ Patient optional) | `medication_dispense` |
| ambiguous | 12 | balanced mixes with no dominant category, empty, or Patient-only | `unknown` |

  Vary `Bundle.type` across `collection`, `transaction` and `batch`, and shuffle entry order. Generated bundle labels are `difficulty: "easy"`, with a rationale naming the template and `approved_by: "construction"`.
- **Quality: 30 generated** (20 Patients + 10 Observations):
  - Synthetic Indonesian names from a built-in list of 40 given and 40 family names.
  - Addresses use `country: "ID"`, with a city from a built-in list.
  - Well-formed NIKs: a region code from a built-in list, then DDMMYY (day + 40 for women), then a 4-digit sequence.
  - Inject 0–2 defects per resource from: missing field, placeholder value, malformed NIK, future date.
  - Draft label: no defects → `auto_accept` / `[70, 100]`; otherwise `review_needed` / `[0, 70]`, with `rationale` listing the injected defects and `approved_by: null`.
- Labels are written into the shared `labels/*.json` by **replacing only entries with `source: "generated"`**, so unit, hard and demo entries are preserved.

**Step 5 — Demo presets (`benchmarks/dataset/demo/`, 6 files, `source: "demo"`, `difficulty: "easy"` unless noted):**
- `patient_complete_jakarta.json`
- `patient_nik_dotted_jakarta.json` (hard)
- `bundle_lab_submission_9_entries.json`
- `condition_je_bali.json`
- `condition_dbd_text_only.json` (hard)
- `bundle_ambiguous_referral.json` (hard)

These must look realistic: full names, addresses, practitioner, dates in 2026. They're **all synthetic**.

**Step 6 — Benchmark runner `--dataset {unit,full}`:**
- `unit` (default) keeps `make bench` fast.
- `full` loads every label with its fixture from all tiers.
- Every module result gains:

```json
"breakdown": {
  "source":     {"unit": {"count": 0, "jev_accuracy": 0.0, "rule_accuracy": 0.0}, "hard": {}, "generated": {}, "demo": {}},
  "difficulty": {"easy": {}, "hard": {}}
},
"unapproved_labels": 0
```

- The Markdown report prints the breakdown tables and a warning line if `unapproved_labels > 0`.
- Makefile: `dataset`, `bench-full` (mock), `bench-live-full` (`MOCK_JEV=false … --live --dataset full`).

**Step 7 — Tests (`tests/test_dataset.py`):**
- Every file under `benchmarks/dataset/` and `tests/fixtures/` parses with `fhir.resources.R4B` (`get_fhir_model_class` from `fhir.resources.R4B`), parametrised.
- Every label loads with its model; every `fixture` path exists; no fixture is labelled twice; no fixture file is unlabelled.
- Count thresholds (see the checklist).
- `generate_dataset.py --check` passes (determinism).
- Hard-case coverage: at least one file per row of the Step 3 lists.
- The rule baseline gets the seven sub-code (A15.0, B50.9, A01.0), SNOMED-only and text-only condition cases **wrong**. This proves the dataset contains discriminating cases. A91 is in the reference list, so the rules get it right; it's there to test display handling, not to beat the rules.
- `make test` runtime stays within ~2× of before. Parametrised validity tests are fine; don't run modules over the generated set in unit tests.

**Step 8 — Verify:**

```bash
make lint && make typecheck && make test
make dataset && git diff --exit-code benchmarks/dataset/generated   # deterministic
make bench && make bench-full
```

**Step 9 — Manual (Budi):**
- Review `labels/*.json` entries with `approved_by: null` and set them to `"budi"`, editing any label you disagree with.
- Answer Open Questions 9 and 10.
- Run `make bench-live-full` and commit the report.

### Codex Evaluation Checklist (re-evaluation after rework, Sep 24, 2026; final)

```
✅ make lint / typecheck / test green; coverage ≥ 95%; runtime ≤ 2× D0
   → 340 passed, 97% coverage, 3.3 s (D0: 4.2 s). baselines/quality.py 100% (was 75%). scripts/ passes ruff + mypy --strict
✅ benchmarks/ground_truth/ deleted; labels/ has quality.json, bundle_routes.json, notifiable.json
✅ tests/fixtures/observations → 10 files, all valid
✅ Hard set: 14 conditions, 9 patients, 5 bundles; content now matches Step 3:
   realistic_lab_submission = Patient+Encounter+DiagnosticReport+6 Observations (each refs Patient + Encounter);
   immunization_with_context = Patient+Encounter+Practitioner+2 Immunization; medication_transaction = transaction,
   every entry has request + fullUrl; vitals_only = 4 vital-sign Observations (8867-4, 9279-1, 8310-5, 59408-5,
   category vital-signs); genuinely_mixed = 3 Obs + 2 Imm + 1 Dispense; *_snomed_only use http://snomed.info/sct;
   A91 has display "Dengue haemorrhagic fever"
✅ Totals: bundles 102, quality 71 (51 Patient + 20 Observation), conditions 31
✅ Route categories: lab 24, encounter 19, immunization 19, medication 19, unknown 21
✅ Every label: source, difficulty, rationale ≥ 10; each fixture labelled once; 0 unlabelled
✅ 204/204 files valid R4B AND valid against the official HL7 R4 4.0.1 JSON schema
✅ No ICD-10 A02–A09
✅ make dataset-check exit 0; two regenerations byte-identical and equal to committed generated/
✅ Generator: no field_completeness / baselines / MockJevClient; no datetime.now / uuid4 / time.time
✅ Generated patients: Indonesian names from lists (11 family / 17 given across 20), 8 cities, 16-digit NIKs consistent
   with birthDate + gender (the 4 mismatches are exactly the injected future-birthDate defects — expected)
✅ Generated quality: 12 clean + 18 with defects; rationales list the defect; invisible defects present
   (placeholder name, future birthDate, NIK with letters, future effectiveDateTime)
✅ Generated bundles: 24 collection / 26 transaction / 30 batch; 0–30 entries (22 with ≥ 10); transaction/batch
   entries all have request + fullUrl; rationales state composition
✅ make bench-full: JSON + Markdown both have per-module source/difficulty tables and the
   "N labels not yet approved by a human" warning
✅ Rule baseline wrong on realistic_lab_submission and on all 7 discriminating hard conditions
✅ make bench (unit) works; router 0.733/0.933 and notifiable 1.000/1.000 unchanged
✅ Validator restored to `upper >= 70`; 0 review labels with passing NIK reach 70
✅ .gitignore no longer ignores benchmark reports
✅ approved_by: 124 null (all unit/hard/demo/generated-quality), 80 "construction" (generated bundles only)
✅ Demo presets realistic: Nadia Ayu Pratama (NIK consistent with 1990-03-02 female; dotted variant = same number),
   9-entry lab submission, 6-entry referral across 6 types, conditions with onset/recorded/recorder
✅ Demo condition_je_bali fixed (Sep 24, Claude Code): ICD-10 "A83" → "A83.0" ("Japanese encephalitis").
   Rule and mock now flag it (rule_correct True). Regression test:
   test_easy_notifiable_labels_are_caught_by_exact_code_rules — every easy confirmed_notifiable label must be
   flagged by the exact-code rule; shown to fail on the old A83 fixture
✅ Generated encounter_summary bundles fixed (Sep 24, Claude Code): generate_dataset.py condition() takes the Encounter
   reference; every Condition now carries encounter.reference "Encounter/generated-encounter-NNN". Regenerated —
   exactly the 18 encounter bundles changed, nothing else; make dataset-check exit 0. Generated router rule accuracy
   0.725 → 0.950; the 4 remaining misses are genuine (ambiguous mixes the rule order sends to immunization_report).
   Regression test: test_generated_encounter_bundles_link_conditions_to_their_encounter
☐ (manual, Budi) all hard + quality labels approved_by=budi; Open Questions 9, 10 answered
☐ (manual, Budi) live full report committed: mode=live_jev, dataset=full, unapproved_labels=0
```

**Minor issues (non-blocking):**

```
⚠️ Defects are assigned round-robin (letters → placeholder → future date, repeating), always exactly one per resource,
   every future birthDate is 2031-03-02, and no Patient gets a missing-field defect (Step 4: 0–2 defects chosen by
   the seeded RNG from all four kinds)
⚠️ Generated patients with a valid NIK (clean + placeholder + future-date) have expected_nik_valid null instead of
   true, so the benchmark skips the NIK check for them
⚠️ Bundle fullUrls use "urn:uuid:generated-18-0"; FHIR requires urn:uuid values to be real UUIDs (schema accepts it)
```

### Evaluation Record

```
Evaluated: Sep 24, 2026 by Claude Code (re-evaluation after Codex rework; the 2 remaining ❌ fixed in the same session)
Counts:    bundles=102 quality=71 conditions=31 hard=28 generated=110 (80 bundles, 20 Patients, 10 Observations)
           demo=6; generated quality 12 clean / 18 defective; bundle types 24/26/30; entries 0–30
Checks:    make lint / typecheck clean; make test 342 passed, 97% coverage, 3.3 s; scripts/ ruff + mypy clean;
           make dataset-check exit 0; 204/204 files valid R4B and valid against the HL7 R4 4.0.1 JSON schema
Results:   all first-evaluation ❌ fixed; both re-evaluation ❌ fixed with regression tests; 3 minor ⚠️ remain
Mock full: quality Jev 0.620 / rule 0.549; router 0.824 / 0.922 (generated 0.863 / 0.950);
           notifiable 0.677 / 0.677; hard tiers: quality 0.222 / 0.222, router 0.600 / 0.600,
           notifiable 0.357 / 0.357. All provisional: labels unapproved
Verdict:   PASS (automated items). Manual items remain for Budi: approve the hard + quality labels, answer Open
           Questions 9 and 10, commit a live full report.
```

<details><summary>First evaluation (history)</summary>

#### First evaluation (Sep 24, 2026): FAIL, superseded by the re-evaluation below

```
✅ make lint / typecheck / test green; coverage ≥ 95%; runtime ≤ 2× D0
   → 337 passed, 96% coverage, 3.2 s (D0: 120 tests, 4.2 s). scripts/ also passes ruff + mypy --strict.
   ⚠️ baselines/quality.py score_observation has no unit test (lines 22–32 uncovered, 75%)
✅ benchmarks/ground_truth/ deleted; labels/ has quality.json, bundle_routes.json, notifiable.json
✅ tests/fixtures/observations → 10 files, all valid R4B
⚠️ Hard set counts met (14 conditions, 9 patients, 5 bundles) and every Step 3 filename exists — BUT content ≠ spec:
   ❌ realistic_lab_submission = 3 Observations (spec: Patient+Encounter+DiagnosticReport+6 labs → the Encounter is the point)
   ❌ immunization_with_context = 1 Immunization (spec: Patient+Encounter+Practitioner+2 Immunization)
   ❌ medication_transaction = type collection, no request (spec: transaction with request entries)
   ❌ vitals_only = Observation + Immunization (spec: 4 vital-sign Observations only)
   ❌ genuinely_mixed = 1 Observation + 1 Immunization (spec: 3 labs + 2 immunizations + 1 dispense)
   ❌ dengue_snomed_only / tb_snomed_only put SNOMED codes (38362002 / 56717001) under the ICD-10 system URL — invalid coding; must be http://snomed.info/sct
   ⚠️ dengue_hemorrhagic_a91 lacks the display "Dengue haemorrhagic fever" from Step 3
✅ Totals: bundles 102, quality 71 (51 Patient + 20 Observation), conditions 31
✅ Route categories: lab 24, encounter 19, immunization 19, medication 19, unknown 21
✅ Every label has source, difficulty, rationale ≥ 10 chars; every fixture labelled exactly once; 0 unlabelled; 204/204 files valid R4B
✅ No ICD-10 A02–A09 in any label fixture
✅ generate_dataset.py --check exit 0; two runs into temp dirs byte-identical and equal to committed generated/
✅ Generator: no field_completeness / baselines / MockJevClient references
✅ Generator: no datetime.now / uuid4 / time.time
❌ Spot-check generated patients: names are "Generated000…019" with given name "Budi" (spec: 40+40 built-in list);
   NIKs sequential 3173010101900000…019 (spec: region + DDMMYY(+40 female) + seq); address country only (spec: city);
   NO injected defects — all 30 generated quality labels are auto_accept with one generic rationale
   ("controlled completeness"), so the generated quality tier tests nothing (spec: 0–2 defects, rationale lists them)
❌ Generated bundles: all 80 are type collection with 1–2 entries (spec: collection/transaction/batch, 1–30 entries,
   shuffled order, optional Patient/Encounter/Practitioner, LOINC pool). Rules score 1.000 on them — near-copies of unit bundles
⚠️ make bench-full → JSON has dataset=full, breakdown by source + difficulty, unapproved_labels ✅;
   Markdown report has NO breakdown tables and NO unapproved-labels warning (Step 6 requires both) ❌
✅ Rule baseline wrong on all 7 discriminating conditions (tb_subcode_a15_0, malaria_subcode_b50_9, typhoid_subcode_a01_0,
   dengue_snomed_only, tb_snomed_only, dbd_text_only, tb_paru_text_only) — note the two *_snomed_only pass for a
   malformed-coding reason (see above)
✅ make bench (unit) works: quality now 30 (incl. Observations) Jev 0.900 / rule 0.767; router 0.733 / 0.933 and
   notifiable 1.000 / 1.000 unchanged
☐ (manual, Budi) all hard + quality labels approved_by=budi; Open Questions 9, 10 answered
☐ (manual, Budi) live full report committed: mode=live_jev, dataset=full, unapproved_labels=0
```

First-evaluation issues outside the checklist:

```
❌ Label validator loosened: `upper >= 70` → `upper > 70` in QualityLabel._action_consistent, so review_needed
   with a passing NIK may now end at exactly 70 — where a score of 70 means auto_accept. 14 labels depend on it
   (7 unit Observations, 6 hard patients, 1 demo patient, all band [0, 70]). Fix: bands → [0, 69], restore `>=`.
   (Partly this plan's fault: the Step 2 table suggested "30–70"/"20–70" review bands.)
❌ .gitignore now ignores benchmarks/results/bench_*.{json,md}. This contradicts Step 9 / D0 Step 15
   ("commit the live report") and D4 (Benchmarks screen shows committed reports). Existing 10 reports stay
   tracked only because they were committed earlier. Fix: remove the rule (or force-add evidence reports).
⚠️ 30 unit route/notifiable labels have approved_by "existing-unit-suite" — an agent-assigned approval, not a
   human one. Recommend null so they show as unapproved until Budi reviews them.
⚠️ Demo presets not "realistic-looking" (Step 5): both patients are the same "Sari Wijaya", address text only
   (no city), no practitioner, conditions have no dates; bundle_lab_submission_9_entries has 3 entries.
⚠️ `make dataset` runs `--check` only, so it can't regenerate the corpus (Step 4: `make dataset` generates).
⚠️ score_observation treats a numeric value of 0 as missing (`bool(state["value"])`).
ℹ️ labels.py still uses `__import__("json")` instead of `import json` (cosmetic).
```

First evaluation record:

```
Evaluated: Sep 24, 2026 by Claude Code (independent session review)
Counts:    bundles=102 quality=71 conditions=31 hard=28 generated=110 demo=6 (204 labelled files, all valid R4B)
Results:   11 ✅, 3 ⚠️, 3 ❌ on the checklist + 2 ❌ / 4 ⚠️ outside it (details above)
What works: structure, label schema/migration, counts, determinism, R4B validity, per-source/difficulty
            breakdown in JSON, and the core goal — rules fail all 7 discriminating hard conditions.
What fails: the hard bundles (5/5) and SNOMED conditions don't match Step 3; the generator (Step 4) produces
            trivial, defect-free data with placeholder names; the Markdown report lacks the breakdown; the
            label validator was weakened; benchmark reports are git-ignored.
Verdict:   FAIL — fix the ❌ items (hard bundles, SNOMED coding, generator realism + defects, MD breakdown,
           validator + [0,69] bands, .gitignore), then re-evaluate. Manual items remain for Budi.
```

</details>

---

## Phase D1: Demo API

**Depends on:** D0.5 PASS (the catalog is built from `labels/`).
**Requirement refs:** DEMO-API-1…7, DEMO-BE-2…11, Demo Plan §4.

### How D1 Is Organised

D1 is specified once and built in five small, sequential sub-phases:

- **D1 Contract (source of truth):** Steps 1–10b below are the unchanged D1 specification: schemas, signatures, lane-policy strings, security rules, route table, SSE wire format, pipeline behaviour, static serving, test requirements and Step 10b. Sub-phases only decide **when** each part is built. If a sub-phase description and the contract ever disagree, **the contract wins**.
- **Sub-phases D1a → D1e:** each is implemented and evaluated separately (Codex implements, then a fresh session evaluates), in this order:

```
D1a Foundations → D1b Compare API → D1c Feed & Pipeline → D1d SSE → D1e Benchmarks, static, final regression
```

- **Rules for every sub-phase:**
  - Tests use the mock Jev client only.
  - Demo routes stay absent when `DEMO_ENABLED=false`.
  - Don't change fixtures, labels, approvals, `.gitignore`, or D0/D0.5 behaviour.
  - Don't start D2 or add frontend code.
  - The existing `tests/test_api.py` must pass unchanged at the end of every sub-phase.
  - Anything listed under "Deferred" must not be implemented early.
- **Final state:** once D1e passes, the code must match the full contract exactly, and the final end-to-end checklist in D1e (the original D1 checklist) must pass.

### D1 Contract (Source of Truth)

**Goal:** everything the UI needs, as mock-testable HTTP endpoints under `/api/v1/demo`, mounted only when `DEMO_ENABLED=true`. No frontend yet.

**Step 1 — Settings:**

```python
demo_enabled: bool = False
demo_pipeline_max_concurrency: int = 4
demo_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
demo_results_dir: Path = PROJECT_ROOT / "benchmarks" / "results"
demo_web_dist: Path = PROJECT_ROOT / "web" / "dist"
```

`.env.example` gets `DEMO_ENABLED=true`.

**Step 2 — Schemas (`demo/schemas.py`):**

```python
DemoModule = Literal["quality", "router", "notifiable"]
Lane = Literal["auto_accepted", "routed", "flagged", "review"]


class Thresholds(BaseModel):
    quality_threshold: int = Field(ge=0, le=100)
    route_confidence_minimum: float = Field(ge=0.0, le=1.0)
    notifiable_confirmed: float = Field(ge=0.0, le=1.0)
    notifiable_review: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _review_below_confirmed(self) -> "Thresholds": ...   # notifiable_review <= notifiable_confirmed

    @classmethod
    def from_settings(cls, settings: Settings) -> "Thresholds": ...


class ThresholdOverrides(BaseModel):
    quality_threshold: int | None = Field(default=None, ge=0, le=100)
    route_confidence_minimum: float | None = Field(default=None, ge=0.0, le=1.0)
    notifiable_confirmed: float | None = Field(default=None, ge=0.0, le=1.0)
    notifiable_review: float | None = Field(default=None, ge=0.0, le=1.0)

    def apply(self, base: Thresholds) -> Thresholds: ...   # re-validates the merged result


class DemoConfig(BaseModel):
    mode: Literal["mock", "live"]
    jev_model: str | None
    thresholds: Thresholds
    route_options: list[str]
    questions: dict[str, str]     # QUALITY_SCORE_QUESTION, NIK_VALIDATION_STATEMENT, ROUTE_QUESTION, NOTIFIABLE_STATEMENT


class FixtureEntry(BaseModel):
    id: str                       # root-relative path; the only accepted fixture identifier
    name: str                     # file stem, e.g. "complete_patient"
    module: DemoModule
    resource_type: str
    source: Source
    difficulty: Difficulty
    label: str                    # short human text, e.g. "auto_accept · 70–100 · NIK ✓"
    ground_truth: dict[str, Any]  # the label minus fixture/source/difficulty
    approved: bool


class CompareRequest(BaseModel):
    resource: dict[str, Any]
    resource_type: Literal["Patient", "Observation"] | None = None   # quality only; default resource.resourceType
    fixture_id: str | None = None                                    # enables ground truth + verdict
    thresholds: ThresholdOverrides | None = None


class RuleDecision(BaseModel):
    decision: str                 # action / category / status, same vocabulary as jev_decision
    score: int | None = None
    nik_valid: bool | None = None


class Verdict(BaseModel):
    jev_correct: bool | None      # None when no ground truth
    rule_correct: bool | None


class CompareResponse(BaseModel):
    module: DemoModule
    jev: QualityScoreResponse | BundleRouteResponse | NotifiableDetectionResponse
    jev_decision: str             # quality → action, router → category, notifiable → status
    jev_raw: list[JevCall]
    rule: RuleDecision
    ground_truth: dict[str, Any] | None
    verdict: Verdict
    serialized_state: dict[str, Any]
    override_applied: bool        # router: model choice replaced by "unknown"
    lane: Lane
    lane_reason: str
    audit_event: dict[str, Any]   # R4 AuditEvent (AuditEventBuilder)
    thresholds: Thresholds        # effective values used
    tokens_used: int
```

**Step 3 — Lane policy (`demo/lanes.py`, a pure function):**

```python
def assign_lane(module: DemoModule, response: BaseModel, thresholds: Thresholds,
                override_applied: bool) -> tuple[Lane, str]: ...
```

| Module | Condition | Lane | `lane_reason` (exact format) |
| --- | --- | --- | --- |
| quality | `action == auto_accept` | `auto_accepted` | `score {s} ≥ threshold {t}` |
| quality | `score < threshold` | `review` | `score {s} < threshold {t}` |
| quality | score passes, NIK gate fails (`nik_valid is False`) | `review` | `NIK gate failed: P(valid) {p:.2f}` |
| router | category ≠ unknown | `routed` | `{category} @ {confidence:.2f}` |
| router | unknown, `override_applied` | `review` | `confidence {c:.2f} < floor {f:.2f}` |
| router | unknown, not overridden | `review` | `model chose unknown` |
| notifiable | `confirmed_notifiable` | `flagged` | `P(notifiable) {p:.2f} ≥ {confirmed:.2f}` |
| notifiable | `review_needed` | `review` | `P(notifiable) {p:.2f} in review band` |
| notifiable | `not_notifiable` | `auto_accepted` | `P(notifiable) {p:.2f} < {review:.2f}` |

Jev errors in the pipeline use lane `review` with the reason `jev error: {error_code}` (see Step 7).

**Step 4 — Fixture catalog (`demo/catalog.py`):**

```python
class FixtureCatalog:
    def __init__(self, labels_dir: Path) -> None: ...     # loads all three label files once
    def entries(self, *, module: DemoModule | None = None, source: Source | None = None,
                difficulty: Difficulty | None = None) -> list[FixtureEntry]: ...
    def get(self, fixture_id: str) -> FixtureEntry | None: ...
    def load_resource(self, fixture_id: str) -> dict[str, Any]: ...   # KeyError if id not in catalog
```

**Security:** only ids present in the catalog can be loaded (an allow-list), so path traversal is impossible by construction. Never join a user-supplied string onto a path.

**Step 5 — Comparer (`demo/compare.py`):**

```python
class Comparer:
    def __init__(self, jev_client: JevClient, catalog: FixtureCatalog, base_thresholds: Thresholds,
                 disease_data_path: Path) -> None: ...

    async def compare(self, module: DemoModule, request: CompareRequest) -> CompareResponse: ...
```

For each call:
1. Create `RecordingJevClient(self._jev_client)` and **fresh module instances** around it (`QualityScorer`, `BundleRouter`, `NotifiableDiseaseDetector`). They're cheap, and this keeps concurrent requests from mixing recorded calls.
2. Effective thresholds are `request.thresholds.apply(base)`.
3. Run the Jev module with those thresholds, run the rule baseline, and build `serialized_state` from the same serializer the module uses.
4. `override_applied` (router): the top choice in `jev_raw[0].result` ≠ `unknown` and `response.category == "unknown"`.
5. `ground_truth` and `verdict`: only when `fixture_id` is in the catalog. Quality compares `action` with `expected_action`; the router compares category; notifiable compares `status == confirmed_notifiable` with `expected_notifiable`.
6. Rule decision vocabulary: quality → `auto_accept` if the rule score ≥ threshold **and** the rule's `nik_valid is not False` (the same NIK gate as `QualityScorer` and the benchmark), else `review_needed`. Use `baselines.quality.score_patient` for Patients and `score_observation` for Observations. Router → category; notifiable → `confirmed_notifiable` or `not_notifiable`. *(Updated after D0/D0.5: NIK gate and Observation baseline.)*
7. Build the `audit_event` with `AuditEventBuilder` (timestamp `datetime.now(UTC)`), and assign the lane.

`ValueError` from modules propagates, so the existing 400 handler applies.

**Step 6 — Decision feed (`demo/feed.py`):**

```python
class DecisionEvent(BaseModel):
    seq: int
    timestamp: datetime
    run_id: str | None
    fixture_id: str | None
    module: DemoModule
    resource_reference: str
    decision: str
    confidence: float
    lane: Lane
    lane_reason: str
    latency_ms: float             # module latency
    jev_latency_ms: float         # sum of jev_raw latencies
    tokens_used: int
    ground_truth_match: bool | None
    error: str | None = None


class RunEvent(BaseModel):
    run_id: str
    status: Literal["started", "finished", "stopped"]
    total: int
    processed: int


class DecisionFeed:
    def __init__(self, maxlen: int = 500) -> None: ...
    def publish(self, event: DecisionEvent | RunEvent) -> int: ...   # assigns the next seq and returns it
    def recent(self, limit: int = 50) -> list[DecisionEvent]: ...    # newest first; decisions only
    def since(self, seq: int) -> list[tuple[int, DecisionEvent | RunEvent]]: ...  # for Last-Event-ID replay
    def subscribe(self) -> "Subscription": ...   # async context manager + async iterator of (seq, event)
```

- Each subscriber has an `asyncio.Queue(maxsize=1000)`. On overflow, drop the oldest item for that subscriber only.
- Everything runs on one event loop, so no locks are needed.
- The ring buffer (`collections.deque(maxlen)`) stores `(seq, event)` for both event kinds.

**Step 7 — Pipeline runner (`demo/pipeline.py`):**

```python
class PipelineRunRequest(BaseModel):
    source: Literal["all", "unit", "hard", "generated", "demo"] = "unit"
    modules: list[DemoModule] = ["quality", "router", "notifiable"]
    rate_per_s: float | None = Field(default=4.0, gt=0, le=50)   # None = as fast as concurrency allows
    thresholds: ThresholdOverrides | None = None


class PipelineRunResponse(BaseModel):
    run_id: str
    total: int
    status: Literal["started"]


class PipelineRunner:
    def __init__(self, catalog: FixtureCatalog, comparer: Comparer, feed: DecisionFeed,
                 max_concurrency: int) -> None: ...
    async def start(self, request: PipelineRunRequest) -> PipelineRunResponse: ...
    async def stop(self, run_id: str) -> bool: ...
    async def shutdown(self) -> None: ...        # called from lifespan on exit
```

- **One active run at a time.** `start()` stops any active run first, publishing `RunEvent(status="stopped")`.
- Order is deterministic: catalog order filtered by `source` and `modules`.
- Pacing: launch one item every `1 / rate_per_s` seconds, with an `asyncio.Semaphore(max_concurrency)` limiting in-flight items. Each item calls `comparer.compare(module, CompareRequest(resource=..., fixture_id=id, thresholds=...))` and publishes a `DecisionEvent` with the `run_id`.
- An item that raises `JevClientError` publishes a `DecisionEvent` with `lane="review"`, `lane_reason=f"jev error: {e.error_code}"`, `error=e.error_code`, `decision="error"` and `confidence=0.0`. The run continues.
- Publish `RunEvent` `started` → (decisions) → `finished` or `stopped`. Runs are finite (bounded by catalog size), so an abandoned browser tab can't leave a run going forever.
- The task is created with `asyncio.create_task`. Keep a reference and cancel it in `stop()` and `shutdown()`.

**Step 8 — Routes (`routes/demo.py`, prefix `/api/v1/demo`, tag `demo`):**

| Method + path | Handler behaviour | Response |
| --- | --- | --- |
| `GET /config` | `DemoConfig` from Settings and module constants | `DemoConfig` |
| `GET /fixtures?module=&source=&difficulty=` | `catalog.entries(...)` | `list[FixtureEntry]` |
| `GET /fixtures/{fixture_id:path}` | `catalog.load_resource`; unknown id → 404 `not_found` | raw FHIR JSON |
| `POST /compare/{module}` | `comparer.compare`; also publishes a `DecisionEvent` (`run_id=None`) | `CompareResponse` |
| `GET /decisions?limit=50` (1–500) | `feed.recent(limit)` | `list[DecisionEvent]` |
| `GET /decisions/stream?limit=` | SSE (below) | `text/event-stream` |
| `POST /pipeline/run` | `runner.start` | `PipelineRunResponse` |
| `POST /pipeline/{run_id}/stop` | `runner.stop`; unknown → 404 | `{"stopped": bool}` |
| `GET /benchmarks` | list `bench_*.json` in `demo_results_dir`, newest first | `list[BenchmarkSummary]` |
| `GET /benchmarks/{name}` | name must match `^bench_[0-9]{8}T[0-9]{6}Z$`, else 404 | report JSON |

```python
class BenchmarkSummary(BaseModel):
    name: str                     # "bench_20260924T085042Z"
    generated_at: datetime
    mode: str
    dataset: str                  # "unit" for pre-D0.5 reports that lack the field
    jev_model: str | None
```

The on-demand benchmark run (`POST /benchmarks/run`) is **out of scope**.

**SSE wire format:**

```
id: 42
event: decision
data: {"seq":42,"timestamp":"…","run_id":"…","module":"router",…}

id: 43
event: run
data: {"run_id":"…","status":"finished","total":60,"processed":60}

: ping
```

- On connect, if a `Last-Event-ID` header is present, replay `feed.since(id)` first.
- Send a `: ping` comment every 15 s.
- Stop when `await request.is_disconnected()`, or after `limit` events when `?limit=` is given (used by tests and curl).
- Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
- Use `StreamingResponse`; don't add a new dependency.

**Step 9 — Wiring (`dependencies.py`, `main.py`):**

```python
@dataclass(frozen=True)
class DemoServices:
    catalog: FixtureCatalog
    comparer: Comparer
    feed: DecisionFeed
    pipeline: PipelineRunner

# AppServices gains: demo: DemoServices | None
def get_demo(request: Request) -> DemoServices: ...   # raises HTTP 404 if demo is None
```

- In `lifespan`, when `settings.demo_enabled`, build `DemoServices`; on exit, `await pipeline.shutdown()`.
- Include `routes.demo.router` **only when `demo_enabled`**, so the paths don't exist otherwise.
- When `demo_enabled`, add `CORSMiddleware(allow_origins=settings.demo_cors_origins, allow_methods=["GET","POST"], allow_headers=["*"], expose_headers=["X-Request-Id","X-Request-Duration-Ms"])`.
- **Static (`demo/static.py`):** when `demo_enabled` and `demo_web_dist/index.html` exists, register `GET /demo` and `GET /demo/{path:path}`. These serve the file if it exists under `demo_web_dist` (resolved path must stay inside it), otherwise `index.html` (SPA fallback). Register `GET /` → 307 redirect to `/demo`. If `web/dist` is missing, `/demo` returns a 503 JSON `{"error":"ui_not_built","detail":"run make web-build"}`.

**Step 10 — Tests (`tests/test_demo_catalog.py`, `test_demo_compare.py`, `test_demo_feed.py`, `test_demo_pipeline.py`, `test_demo_api.py`):** all mock. `create_app(Settings(mock_jev=True, demo_enabled=True))`; use a temporary `demo_results_dir` with two copied reports.
- Demo disabled → `/api/v1/demo/config` returns 404 (the route doesn't exist).
- Catalog totals match the label files; filters work; ids are root-relative.
- `GET /fixtures/../../.env` and `/fixtures/%2e%2e/.env` → 404; `.env` content is never returned.
- Compare quality on `complete_patient` → `jev_decision == "auto_accept"`, `rule.decision` present, `serialized_state.field_completeness` present, `jev_raw` has one `score` and one `noul`, `tokens_used > 0`, and the `audit_event` parses as R4B.
- Compare router on `mixed_bundle` with `route_confidence_minimum=0.99` → `category == "unknown"`, `override_applied is True`, `lane == "review"`, and `lane_reason` starts with `"confidence"`.
- Compare notifiable on `japanese_encephalitis_a83` → `lane == "flagged"`, `flag_resource` not None, `verdict.jev_correct is True`.
- Compare quality on `invalid_nik` → `jev_decision == "review_needed"`, `rule.decision == "review_needed"`, `lane == "review"`, and `lane_reason` starts with `"NIK gate failed"`. The score passes, so the NIK gate is the cause.
- Compare quality on an Observation fixture (`tests/fixtures/observations/missing_value.json`) → `rule.score` comes from `score_observation`, `jev_raw` has only a `score` call (no `noul`).
- `ThresholdOverrides` with `notifiable_review > notifiable_confirmed` → 422.
- `assign_lane`: one test per table row (8 tests).
- Feed: `maxlen` cap at 500; `recent` is newest-first; `since` replay; a slow subscriber overflow drops the oldest for that subscriber only.
- Pipeline: `rate_per_s=None` over `source="unit"` → exactly `total` decision events plus `started` and `finished` run events. A second `start` stops the first (`stopped` event). An injected `JevTimeoutError` on one item → that event has `lane == "review"` and `error == "jev_timeout"`, and the run still finishes.
- SSE endpoint: `GET /decisions/stream?limit=3` after a pipeline run → the body has 3 `event:` blocks in the wire format, with `id:` lines.
- Benchmarks: list is sorted newest-first; a bad name → 404; a pre-D0.5 report without `dataset` → `"unit"`.
- Static: with a temp `demo_web_dist` holding `index.html` and `assets/app.js`, `/demo/studio` → index.html, `/demo/assets/app.js` → the file, `/demo/../../pyproject.toml` → never served.
- Phase 4 regression: existing `test_api.py` passes unchanged, and the Phase 4 response schemas in `/openapi.json` are unchanged (snapshot compare of the three response models).

**Step 10b — Makefile:** change `serve` to `$(PYTHON) -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000`, matching the other targets, which use `.venv/bin/python` since D0.5.

### D1 Implementation Sequence

The pre-D1 baseline is **342 tests** (end of D0.5). Contract Step 10's test list is distributed across the sub-phases below; each contract test appears in exactly one of them.

---

#### Phase D1a — Foundations

**1. Dependencies:** D0.5 PASS (it does, for automated items).

**2. Scope and files:**
- `src/jev_fhir/config.py`: all Step 1 settings (`demo_enabled`, `demo_pipeline_max_concurrency`, `demo_cors_origins`, `demo_results_dir`, `demo_web_dist`). Settings used by later sub-phases are added now so Settings changes only once.
- `.env.example`: add `DEMO_ENABLED=true` (Step 1).
- `src/jev_fhir/demo/__init__.py` (new).
- `src/jev_fhir/demo/schemas.py` (new): every Step 2 model: `DemoModule`, `Lane`, `Thresholds` (with `_review_below_confirmed` and `from_settings`), `ThresholdOverrides.apply`, `DemoConfig`, `FixtureEntry`, `CompareRequest`, `RuleDecision`, `Verdict`, `CompareResponse`.
- `src/jev_fhir/demo/catalog.py` (new): the Step 4 `FixtureCatalog`, loading all three label files from `settings.labels_dir` once. It's an allow-list, and `load_resource` raises `KeyError` for unknown ids.
- `src/jev_fhir/routes/demo.py` (new): `router = APIRouter(tags=["demo"])` with **no endpoints yet**.
- `src/jev_fhir/dependencies.py`: add `DemoServices` and `get_demo` (Step 9), plus `AppServices.demo: DemoServices | None`. In D1a, `DemoServices` holds only `catalog`; D1b adds `comparer`, and D1c adds `feed` and `pipeline`, reaching the exact Step 9 shape.
- `src/jev_fhir/main.py`:
  - In lifespan, build `DemoServices` only when `settings.demo_enabled`; otherwise `demo=None`.
  - Include `routes.demo.router` at prefix `/api/v1/demo` **only when `demo_enabled`** (Step 9).

**3. Acceptance criteria:**
- With `demo_enabled=False`: `app.state.services.demo is None`, and no route path in `app.routes` or `/openapi.json` starts with `/api/v1/demo`.
- With `demo_enabled=True`: `services.demo.catalog` is a `FixtureCatalog`.
- `FixtureCatalog` entries match the label files: 204 entries, ids root-relative, `module` derived from the label file, `approved` equals `approved_by is not None`. The `module`, `source` and `difficulty` filters work.
- `Thresholds` and `ThresholdOverrides` enforce the Step 2 bounds and `notifiable_review <= notifiable_confirmed`, including after `apply()` merges overrides.
- Nothing from D1b–D1e exists yet.

**4. Tests to add:**
- `tests/test_demo_catalog.py`:
  - contract test "Catalog totals match the label files; filters work; ids are root-relative."
  - `get()` returns None for unknown ids
  - `load_resource` raises `KeyError` for unknown ids, including `../../.env`-style ids, without touching the filesystem
  - `FixtureEntry.label` is non-empty
- Schema tests (in `test_demo_catalog.py` or a new `tests/test_demo_schemas.py`):
  - `Thresholds` rejects `notifiable_review > notifiable_confirmed`
  - `ThresholdOverrides.apply` merges and re-validates
  - `Thresholds.from_settings` maps the four Settings fields
- `tests/test_demo_api.py` (new), foundations:
  - disabled → `services.demo is None` and no `/api/v1/demo` routes
  - enabled → `DemoServices.catalog` present
  - `tests/test_api.py` unchanged and passing

**5. Verification:**

```bash
make lint && make typecheck && make test      # coverage ≥ 95%; demo/schemas.py and demo/catalog.py ≥ 90%
.venv/bin/python -m pytest -q tests/test_demo_catalog.py tests/test_demo_api.py
```

**6. Deferred:**
- to D1b: every endpoint, `Comparer`, `lanes.py`, and the HTTP-level "demo disabled → `/api/v1/demo/config` 404" contract test
- to D1c: `feed.py`, `pipeline.py`, the `feed`/`pipeline` fields on `DemoServices`, and lifespan shutdown
- to D1d: SSE
- to D1e: CORS, static serving, benchmarks endpoints, Makefile Step 10b, and the OpenAPI snapshot

**D1a evaluation checklist:**

```
✅ make lint / typecheck / test green; coverage ≥ 95%; demo/schemas.py and demo/catalog.py ≥ 90%
   → 350 passed (342 → 350), 97% total; schemas.py 100%, catalog.py 97% (line 81, the load_resource success path, is untested)
✅ Step 1 settings present with the exact names and defaults; .env.example has DEMO_ENABLED=true
✅ Step 2 models match the contract field-for-field (names, types, bounds, both validators, from_settings mapping,
   apply() re-validates) — checked by reading schemas.py against Step 2
✅ Disabled app: no route or OpenAPI path starts with /api/v1/demo; services.demo is None
   (test + real server: DEMO_ENABLED=false → health 200, 0 demo paths, clean log)
✅ Enabled app: services.demo.catalog present; catalog has 204 entries matching labels/
   (real server: DEMO_ENABLED=true → health 200, 0 demo paths since the router is empty, clean log)
✅ load_resource on an unknown or traversal-style id raises KeyError without filesystem access
   (test patches Path.read_text to fail; lookup is a dict allow-list built from label paths)
✅ grep catalog.py: no Path join / open() using a caller-supplied string (paths come only from fixture_path(label))
✅ tests/test_api.py passes unchanged (git diff empty); no D1b–D1e code present (routes/demo.py has no endpoints;
   no lanes/compare/feed/pipeline/static modules)
```

**Issues found (first check) and fixes (Sep 25, 2026, Claude Code):**

```
✅ FIXED ❌ Step 2 ground_truth: now the label minus only {"fixture", "source", "difficulty"}, so rationale and
   approved_by are included. Dumped with mode="json" (the score band is a JSON list, as in the label files).
   Test: test_ground_truth_is_label_minus_fixture_source_difficulty (compares every entry with its validated label)
✅ FIXED ❌ Step 4 signature: entries(self, *, module: DemoModule | None = None, source: Source | None = None,
   difficulty: Difficulty | None = None), matching the contract exactly (verified with inspect.signature)
✅ FIXED ⚠️ label NIK marker: " · NIK ✓" / " · NIK ✗" / nothing for True / False / None
   (invalid_nik → "review_needed · 70–100 · NIK ✗"). Test: test_quality_label_marks_nik_expectation
✅ FIXED ⚠️ test_approved_mirrors_labels now compares entry.approved with each label's approved_by. Shown to still hold
   after a simulated approval of the hard + unit labels (the old version would have failed)
✅ FIXED ⚠️ test_catalog_totals derives every count (total, per module, per source, per difficulty) and the id order
   from the label files instead of hard-coding 204 / 71
✅ FIXED ⚠️ new test_load_resource_returns_the_labelled_fixture covers the load_resource success path (catalog.py 100%);
   the difficulty filter is covered by the totals test
✅ FIXED ℹ️ DemoServices docstring no longer names a phase
ℹ️ OPEN (D1b decision) get_demo raises HTTPException(404, "not_found"), so the body is FastAPI's default {"detail": ...},
   not the project's ErrorResponse. No route uses it yet; D1b's /fixtures 404 (`not_found`) should settle it.
   Recommendation: return the ErrorResponse shape for consistency with every other API error.
ℹ️ OPEN (cosmetic) schema classes have no docstrings, unlike the rest of the codebase
```

**D1a evaluation record:**

```
Evaluated: Sep 25, 2026 by Claude Code (fresh-session review); fixes applied and re-checked in the same session
Checks:    make lint / typecheck clean; make test 353 passed (342 → 353), 97% total; demo/catalog.py 100%,
           demo/schemas.py 100%; tests/test_api.py unchanged; real server starts cleanly with demo on and off
Results:   8/8 checklist items ✅; both ❌ contract deviations fixed; all ⚠️ fixed; 2 ℹ️ open (above)
Verdict:   PASS. D1b can start. Settle the get_demo 404 body format in D1b.
```

---

#### Phase D1b — Compare API

**1. Dependencies:** D1a PASS.

**2. Scope and files:**
- `src/jev_fhir/demo/lanes.py` (new): `assign_lane` exactly per Step 3, with the exact `lane_reason` formats, including `NIK gate failed: P(valid) {p:.2f}`.
- `src/jev_fhir/demo/compare.py` (new): the Step 5 `Comparer`:
  - fresh `RecordingJevClient` and module instances per call
  - effective thresholds from `apply()`
  - rule decisions per Step 5.6: NIK gate, with `score_patient` / `score_observation`
  - `serialized_state` built from the module's serializer
  - `override_applied` per Step 5.4
  - ground truth and verdict per Step 5.5
  - an R4 `audit_event` from `AuditEventBuilder`
  - lane assignment and `tokens_used`
  - `ValueError` propagates to the existing 400 handler
- `src/jev_fhir/dependencies.py`: `DemoServices` gains `comparer`.
- `src/jev_fhir/main.py`: build the `Comparer` in lifespan when demo is enabled.
- `src/jev_fhir/routes/demo.py`, from the Step 8 table:
  - `GET /config`
  - `GET /fixtures?module=&source=&difficulty=`
  - `GET /fixtures/{fixture_id:path}`: unknown id → 404 `not_found`
  - `POST /compare/{module}`: in D1b it returns the `CompareResponse` **without** publishing to the feed, because the feed doesn't exist until D1c.

**3. Acceptance criteria:**
- `/config` returns `mode`, `jev_model`, 4 thresholds from Settings, the 5 `ROUTE_OPTIONS`, and the 4 question constants.
- The fixture endpoints serve only catalog ids. Traversal attempts return 404 and never expose `.env` content.
- Compare results match every Step 10 compare case.
- Demo endpoints carry `X-Request-Id` and `X-Request-Duration-Ms`, from the existing middleware.
- Invalid threshold combinations return 422.

**4. Tests to add:**
- `tests/test_demo_compare.py`:
  - contract test "`assign_lane`: one test per table row (8 tests).". The table has **9 rows** since the NIK-gate row was added, so the "8 tests" count is stale. Test all 9. The `jev error:` reason is tested in D1c.
  - `Comparer` unit tests: a fresh `RecordingJevClient` per call (two concurrent `compare()` calls don't mix `jev_raw`); `override_applied` logic; the rule NIK gate.
- `tests/test_demo_api.py`, contract tests:
  - "Demo disabled → `/api/v1/demo/config` returns 404 (the route doesn't exist)."
  - "`GET /fixtures/../../.env` and `/fixtures/%2e%2e/.env` → 404; `.env` content is never returned."
  - "Compare quality on `complete_patient` → `jev_decision == "auto_accept"`, `rule.decision` present, `serialized_state.field_completeness` present, `jev_raw` has one `score` and one `noul`, `tokens_used > 0`, and the `audit_event` parses as R4B."
  - "Compare router on `mixed_bundle` with `route_confidence_minimum=0.99` → `category == "unknown"`, `override_applied is True`, `lane == "review"`, and `lane_reason` starts with `"confidence"`."
  - "Compare notifiable on `japanese_encephalitis_a83` → `lane == "flagged"`, `flag_resource` not None, `verdict.jev_correct is True`."
  - "Compare quality on `invalid_nik` → `jev_decision == "review_needed"`, `rule.decision == "review_needed"`, `lane == "review"`, and `lane_reason` starts with `"NIK gate failed"`. The score passes, so the NIK gate is the cause."
  - "Compare quality on an Observation fixture (`tests/fixtures/observations/missing_value.json`) → `rule.score` comes from `score_observation`, `jev_raw` has only a `score` call (no `noul`)."
  - "`ThresholdOverrides` with `notifiable_review > notifiable_confirmed` → 422."
- `tests/test_demo_api.py`, additional:
  - `/config` shape
  - `/fixtures` filters
  - fixture load by a valid id
  - headers present on the demo endpoints

**5. Verification:**

```bash
make lint && make typecheck && make test      # coverage ≥ 95%; demo/lanes.py and demo/compare.py ≥ 90%
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --port 8000   # then:
curl -s localhost:8000/api/v1/demo/config
curl -s "localhost:8000/api/v1/demo/fixtures?source=hard" | .venv/bin/python -c "import json,sys;print(len(json.load(sys.stdin)))"
curl -s --path-as-is -o /dev/null -w "%{http_code}\n" "localhost:8000/api/v1/demo/fixtures/../../.env"
```

**6. Deferred:**
- to D1c: publishing a `DecisionEvent` from `POST /compare`, the `jev error:` lane reason (pipeline only), `/decisions`, and `/pipeline/*`
- to D1d: SSE
- to D1e: benchmarks, static serving, CORS, Step 10b, and the OpenAPI snapshot

**D1b evaluation checklist:**

```
☐ make lint / typecheck / test green; coverage ≥ 95%; demo/lanes.py and demo/compare.py ≥ 90%
☐ lane_reason strings match the Step 3 table exactly (9 row tests)
☐ curl /api/v1/demo/config → mode=mock, 4 thresholds, 5 route_options, 4 questions
☐ curl "/api/v1/demo/fixtures?source=hard" → ≥ 25 entries
☐ curl "/api/v1/demo/fixtures/tests/fixtures/patients/complete_patient.json" → Patient JSON
☐ curl --path-as-is "/api/v1/demo/fixtures/../../.env" → 404, body has no JEV_API_KEY
☐ POST /compare/router mixed_bundle with {"thresholds":{"route_confidence_minimum":0.99}} → override_applied true, lane review
☐ POST /compare/notifiable JE fixture → lane flagged, audit_event.type present, no audit_event.code
☐ POST /compare/quality invalid_nik → review, lane_reason starts "NIK gate failed"
☐ Two concurrent compare() calls return disjoint jev_raw lists (test name)
☐ Demo endpoint responses include X-Request-Id and X-Request-Duration-Ms
☐ Demo disabled → /api/v1/demo/config 404
☐ tests/test_api.py passes unchanged; no feed / pipeline / SSE / benchmarks / static code present
```

**D1b evaluation record:**

```
Evaluated: <date> by <session>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL
```

---

#### Phase D1c — Feed and Pipeline

**1. Dependencies:** D1b PASS.

**2. Scope and files:**
- `src/jev_fhir/demo/feed.py` (new): the Step 6 `DecisionEvent`, `RunEvent` and `DecisionFeed`:
  - `publish` assigns `seq`
  - `recent` is newest-first and decisions-only
  - `since` supports replay
  - `subscribe` returns an async context manager and iterator, with a per-subscriber `asyncio.Queue(maxsize=1000)` that drops the oldest item on overflow
  - the ring buffer is a `deque(maxlen)` of `(seq, event)` for both event kinds
- `src/jev_fhir/demo/pipeline.py` (new): the Step 7 `PipelineRunRequest`, `PipelineRunResponse` and `PipelineRunner`:
  - one active run at a time; a new `start()` stops the previous run and publishes `stopped`
  - deterministic catalog-order launch
  - pacing plus a `Semaphore(max_concurrency)`
  - `JevClientError` produces a review-lane event with `jev error: {error_code}` and the run continues
  - `started` → decisions → `finished` / `stopped` run events
  - the `create_task` reference is kept and cancelled in `stop()` and `shutdown()`
- `src/jev_fhir/dependencies.py`: `DemoServices` gains `feed` and `pipeline`, reaching the **exact Step 9 shape**.
- `src/jev_fhir/main.py`: build the feed and runner in lifespan (`max_concurrency=settings.demo_pipeline_max_concurrency`); on exit, `await pipeline.shutdown()` (Step 9).
- `src/jev_fhir/routes/demo.py`, from the Step 8 table:
  - `GET /decisions?limit=50` (1–500): the recent-decisions history
  - `POST /pipeline/run`
  - `POST /pipeline/{run_id}/stop`: unknown → 404
  - `POST /compare/{module}` now also publishes a `DecisionEvent` with `run_id=None`, completing the Step 8 row.

**3. Acceptance criteria:**
- Every Step 6 and Step 7 behaviour listed above holds.
- `/decisions` respects `limit` bounds (1–500), with `seq` strictly decreasing.
- A pipeline run over `source="unit"` with `rate_per_s=None` emits exactly `total` decision events, plus `started` and `finished`.
- Lifespan shutdown cancels an in-flight run.

**4. Tests to add:**
- `tests/test_demo_feed.py`, contract test "Feed: `maxlen` cap at 500; `recent` is newest-first; `since` replay; a slow subscriber overflow drops the oldest for that subscriber only.", plus `publish` returning increasing `seq` values.
- `tests/test_demo_pipeline.py`, contract tests:
  - "Pipeline: `rate_per_s=None` over `source="unit"` → exactly `total` decision events plus `started` and `finished` run events. A second `start` stops the first (`stopped` event). An injected `JevTimeoutError` on one item → that event has `lane == "review"` and `error == "jev_timeout"`, and the run still finishes."
  - Also test: lifespan shutdown cancels an in-flight pipeline; pacing respects `rate_per_s` (assert a lower bound on elapsed time for a small run); in-flight items never exceed `max_concurrency`.
- `tests/test_demo_api.py`:
  - `POST /compare` publishes one event, visible in `/decisions`
  - `GET /decisions?limit=3` → 3 items with `seq` strictly decreasing
  - `limit` of 0 or 501 → 422
  - stopping an unknown run → 404

Decision events from a concurrent run may complete out of launch order. Tests must not assume completion order, only counts and the run-event sequence.

**5. Verification:**

```bash
make lint && make typecheck && make test      # coverage ≥ 95%; demo/feed.py and demo/pipeline.py ≥ 90%
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --port 8000   # then:
curl -s -X POST localhost:8000/api/v1/demo/pipeline/run -H 'content-type: application/json' -d '{"source":"unit","rate_per_s":null}'
curl -s "localhost:8000/api/v1/demo/decisions?limit=3"
```

**6. Deferred:**
- to D1d: `GET /decisions/stream`, the SSE wire format, `Last-Event-ID`, ping and `?limit=`. `DecisionFeed.subscribe()` and `since()` are built and unit-tested here, but have no HTTP consumer until D1d.
- to D1e: benchmarks, static serving, CORS, Step 10b, and the OpenAPI snapshot

**D1c evaluation checklist:**

```
☐ make lint / typecheck / test green; coverage ≥ 95%; demo/feed.py and demo/pipeline.py ≥ 90%
☐ DemoServices matches the Step 9 shape exactly (catalog, comparer, feed, pipeline)
☐ POST /pipeline/run {"source":"unit","rate_per_s":null} → run completes; decision count == total
☐ GET /decisions?limit=3 → 3 items, seq strictly decreasing
☐ POST /compare publishes one DecisionEvent (run_id null) visible in /decisions
☐ Injected JevTimeoutError → review lane, lane_reason "jev error: jev_timeout", run finishes (test name)
☐ Second start → first run gets a "stopped" RunEvent (test name)
☐ Lifespan shutdown cancels an in-flight pipeline (test name)
☐ Concurrency never exceeds demo_pipeline_max_concurrency (test name)
☐ tests/test_api.py passes unchanged; no SSE / benchmarks / static / CORS code present
```

**D1c evaluation record:**

```
Evaluated: <date> by <session>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL
```

---

#### Phase D1d — SSE

**1. Dependencies:** D1c PASS.

**2. Scope and files:**
- `src/jev_fhir/routes/demo.py`: `GET /decisions/stream?limit=` using `StreamingResponse` (no new dependency), in the exact SSE wire format from the contract:
  - `id: <seq>`, then `event: decision|run`, then `data: <json>`, then a blank line
  - on connect, if `Last-Event-ID` is present, replay `feed.since(id)` first
  - a `: ping` comment every 15 s
  - stop on `request.is_disconnected()`, or after `limit` events when `?limit=` is given
  - headers `Cache-Control: no-cache` and `X-Accel-Buffering: no`
- The 15 s ping interval is a module-level constant (e.g. `SSE_PING_INTERVAL_S = 15.0`), so tests can shorten it with monkeypatch. The production value stays 15 s.

**3. Acceptance criteria:**
- The wire format matches the contract byte for byte: field order and a blank-line separator. Pings are comments and don't count towards `limit`.
- `Last-Event-ID: N` replays only events with `seq > N`, then continues live.
- The stream closes after `limit` events.
- The disconnect check ends the generator: no orphaned subscriber stays registered in the feed.

**4. Tests to add (`tests/test_demo_api.py`):**
- contract test "SSE endpoint: `GET /decisions/stream?limit=3` after a pipeline run → the body has 3 `event:` blocks in the wire format, with `id:` lines."
- `Last-Event-ID` replay returns only newer events
- `run` events use `event: run`
- the headers are present
- a ping appears when the interval is monkeypatched short
- the subscriber count returns to 0 after the stream ends

**5. Verification:**

```bash
make lint && make typecheck && make test      # coverage ≥ 95%
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --port 8000   # then:
curl -s -X POST localhost:8000/api/v1/demo/pipeline/run -H 'content-type: application/json' -d '{"source":"unit","rate_per_s":null}'
curl -sN "localhost:8000/api/v1/demo/decisions/stream?limit=5"
curl -sN -H "Last-Event-ID: 3" "localhost:8000/api/v1/demo/decisions/stream?limit=2"
```

**6. Deferred:** to D1e: benchmarks, static serving, CORS, Step 10b, the OpenAPI snapshot, and the final end-to-end checklist.

**D1d evaluation checklist:**

```
☐ make lint / typecheck / test green; coverage ≥ 95%
☐ POST /pipeline/run {"source":"unit","rate_per_s":null} then curl "/decisions/stream?limit=5" → 5 SSE blocks with id/event/data
☐ Last-Event-ID: N replays only seq > N (curl + test name)
☐ Response headers: Content-Type text/event-stream, Cache-Control no-cache, X-Accel-Buffering no
☐ ": ping" comment emitted (test with a monkeypatched interval); production constant is 15 s
☐ No subscriber leak after the stream ends (test name)
☐ No new runtime dependency; tests/test_api.py passes unchanged; no benchmarks / static / CORS code present
```

**D1d evaluation record:**

```
Evaluated: <date> by <session>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL
```

---

#### Phase D1e — Benchmarks, Static Serving, and Final Regression

**1. Dependencies:** D1d PASS.

**2. Scope and files:**
- `src/jev_fhir/routes/demo.py`, from the Step 8 table:
  - `GET /benchmarks`: list `bench_*.json` in `demo_results_dir`, newest first
  - `GET /benchmarks/{name}`: `name` must match `^bench_[0-9]{8}T[0-9]{6}Z$`, else 404
  - `BenchmarkSummary`, with `dataset` falling back to `"unit"` and `jev_model` to `None` for older reports
  - `POST /benchmarks/run` stays out of scope
- `src/jev_fhir/demo/static.py` (new), per Step 9:
  - when `demo_enabled` and `demo_web_dist/index.html` exist, `GET /demo` and `GET /demo/{path:path}` serve the file if it resolves inside `demo_web_dist`, otherwise `index.html` (SPA fallback)
  - `GET /` → 307 redirect to `/demo`
  - when `web/dist` is missing, `/demo` returns 503 `{"error":"ui_not_built","detail":"run make web-build"}`
- `src/jev_fhir/main.py`: when `demo_enabled`, add `CORSMiddleware(allow_origins=settings.demo_cors_origins, allow_methods=["GET","POST"], allow_headers=["*"], expose_headers=["X-Request-Id","X-Request-Duration-Ms"])`, and register the static routes.
- `Makefile`: Step 10b, changing `serve` to `$(PYTHON) -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000`.
- An OpenAPI snapshot test: the Phase 4 response schemas (`QualityScoreResponse`, `BundleRouteResponse`, `NotifiableDetectionResponse`) in `/openapi.json` are unchanged.

**3. Acceptance criteria:**
- Benchmarks endpoints behave per Step 8, and a report name can never resolve outside `demo_results_dir`.
- Static serving follows Step 9 exactly, including path containment and the 503 when the UI isn't built.
- CORS is active only when demo is enabled.
- `make serve` works. The Phase 4 schemas are unchanged.
- The code now matches the full D1 contract.

**4. Tests to add (`tests/test_demo_api.py`):**
- contract test "Benchmarks: list is sorted newest-first; a bad name → 404; a pre-D0.5 report without `dataset` → `"unit"`.", using a temporary `demo_results_dir` with two copied reports
- contract test "Static: with a temp `demo_web_dist` holding `index.html` and `assets/app.js`, `/demo/studio` → index.html, `/demo/assets/app.js` → the file, `/demo/../../pyproject.toml` → never served."
- contract test "Phase 4 regression: existing `test_api.py` passes unchanged, and the Phase 4 response schemas in `/openapi.json` are unchanged (snapshot compare of the three response models)."
- Additional:
  - `/demo` → 503 `ui_not_built` when `demo_web_dist` is missing
  - a CORS preflight from `http://localhost:5173` is allowed when enabled and absent when disabled
  - `GET /` → 307 to `/demo`

**5. Verification:**

```bash
make lint && make typecheck && make test
MOCK_JEV=true make serve                      # demo disabled
DEMO_ENABLED=true MOCK_JEV=true make serve    # then run the full final checklist below
```

**6. Deferred:** nothing inside D1. Frontend work (`web/`) starts in D2.

**D1e checks (sub-phase):**

```
☐ GET /benchmarks → newest first; GET /benchmarks/nope → 404; old report without dataset → "unit"
☐ GET /demo without web/dist → 503 ui_not_built
☐ Static tests: SPA fallback, asset served, traversal never served (test names)
☐ CORS preflight allowed only when demo enabled (test name)
☐ make serve uses $(PYTHON) -m uvicorn (Step 10b)
☐ OpenAPI snapshot test for the three Phase 4 response models passes
```

**Final D1 end-to-end checklist (the original D1 checklist, run after D1e):**

```
☐ make lint / typecheck / test green; coverage ≥ 95%; each new demo/*.py ≥ 90%
☐ Test count increased by ≥ 30 (show before/after)
☐ MOCK_JEV=true make serve (demo disabled): curl -s -o /dev/null -w "%{http_code}" :8000/api/v1/demo/config → 404
☐ DEMO_ENABLED=true MOCK_JEV=true make serve, then:
   ☐ curl /api/v1/demo/config → mode=mock, 4 thresholds, 5 route_options, 4 questions
   ☐ curl "/api/v1/demo/fixtures?source=hard" | python -c "…len…" → ≥ 25
   ☐ curl "/api/v1/demo/fixtures/tests/fixtures/patients/complete_patient.json" → Patient JSON
   ☐ curl --path-as-is "/api/v1/demo/fixtures/../../.env" → 404, body has no JEV_API_KEY
   ☐ POST /compare/router mixed_bundle with {"thresholds":{"route_confidence_minimum":0.99}} → override_applied true, lane review
   ☐ POST /compare/notifiable JE fixture → lane flagged, audit_event.type present, no audit_event.code
   ☐ POST /pipeline/run {"source":"unit","rate_per_s":null} then curl "/decisions/stream?limit=5" → 5 SSE blocks with id/event/data
   ☐ GET /decisions?limit=3 → 3 items, seq strictly decreasing
   ☐ GET /benchmarks → newest first; GET /benchmarks/nope → 404
   ☐ GET /demo without web/dist → 503 ui_not_built
☐ Response headers on demo endpoints include X-Request-Id and X-Request-Duration-Ms
☐ grep routes/demo.py and catalog.py: no Path(...) / "/" joins using request-supplied strings
☐ Phase 4 schemas unchanged: openapi snapshot test passes
☐ No new runtime dependency in pyproject.toml
☐ Lifespan shutdown cancels an in-flight pipeline (test name)
☐ Final code matches the full D1 contract (Steps 1–10b): DemoServices shape, route table, lane strings, SSE format
```

**D1e / final D1 evaluation record:**

```
Evaluated: <date> by <session>
Tests:     before D1 = 342 → after D1e = <n>
Results:   <sub-phase checks + final checklist with evidence>
Verdict:   PASS | FAIL
```

---

## Phase D2: UI Shell, Overview, Studio, Playground

**Depends on:** D1 PASS.
**Requirement refs:** UI-G-1…6 (incl. G-1b), UI-O-1…3, UI-S-1…7, UI-PL-1…3, UI-NFR-1…6.

### Codex Implementation

**Goal:** a working web app at `/demo` with the global shell, Overview, the three-column Studio and the Playground, all typed against the backend's OpenAPI schema.

**Prerequisite:** Node.js 20 LTS in WSL (`node --version` → v20.x). It isn't installed on the dev machine today: `node` is missing even though `npm` resolves. Install it with nvm (`nvm install 20`) and confirm before starting.

**Step 1 — Scaffold `web/`:**

```
web/
├── package.json · package-lock.json · tsconfig.json · vite.config.ts · tailwind.config.ts
├── postcss.config.js · eslint.config.js · playwright.config.ts · index.html
├── openapi.json                 # generated, committed
├── e2e/                         # Playwright specs
└── src/
    ├── main.tsx · App.tsx · index.css
    ├── api/      client.ts · schema.d.ts (generated) · types.ts · queries.ts
    ├── lib/      noul.ts · format.ts · colors.ts · debounce.ts
    ├── state/    uiPrefs.tsx     # font scale, presenter notes (localStorage in try/catch)
    ├── components/
    │   ├── shell/   TopBar · ModeBadge · HealthDot · ErrorCard · NavTabs
    │   ├── studio/  FixturePicker · JsonView · FlatStateTable · QuestionBox · DecisionCard
    │   │            ScoreGauge · LevelDistribution · ProbabilityBars · NoulMeter
    │   │            ThresholdSliders · VerdictStrip · ArtifactTabs · LatencyLine · DinkesCard
    │   └── overview/ ArchitectureDiagram · ModuleCard
    └── pages/    Overview · Studio · Playground   (Pipeline, Benchmarks: placeholder routes until D3/D4)
```

Dependencies (pin the major versions):

| Runtime | Dev |
| --- | --- |
| `react@18`, `react-dom@18`, `react-router-dom@6`, `@tanstack/react-query@5`, `recharts@2`, `@uiw/react-json-view@2`, `@uiw/react-codemirror@4`, `@codemirror/lang-json@6`, `@fontsource-variable/inter` | `vite@5`, `@vitejs/plugin-react`, `typescript@5`, `tailwindcss@3`, `postcss`, `autoprefixer`, `openapi-typescript@7`, `vitest@2`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `@playwright/test`, `eslint@9`, `typescript-eslint`, `eslint-plugin-react-hooks` |

`package.json` scripts: `dev`, `build` (`tsc -b && vite build`), `lint`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`), `e2e` (`playwright test`), `types` (`openapi-typescript openapi.json -o src/api/schema.d.ts`).

**Step 2 — Vite config:**

```ts
export default defineConfig({
  base: "/demo/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist", sourcemap: true },
});
```

`BrowserRouter basename="/demo"`. Routes: `/` Overview · `/studio/:module` Studio (`?fixture=<id>`) · `/playground` · `/pipeline` · `/benchmarks`.

**Step 3 — API types and client:**
- `scripts/dump_openapi.py` writes `web/openapi.json` from `create_app(Settings(mock_jev=True, demo_enabled=True)).openapi()`. No server is needed.
- `make web-types` runs `python scripts/dump_openapi.py && cd web && npm run types`. Commit `schema.d.ts`.
- `api/types.ts` re-exports the named types from `components["schemas"]` (`CompareResponse`, `FixtureEntry`, `DemoConfig`, `Thresholds`, `DecisionEvent`, …). **No hand-written duplicates of backend models.**
- `api/client.ts`:

```ts
export class ApiError extends Error {
  constructor(public status: number, public body: ErrorBody, public requestId: string | null) { super(body.error); }
}
export interface LastRequest { requestId: string | null; durationMs: number | null; path: string }
export async function api<T>(path: string, init?: RequestInit): Promise<T>;   // throws ApiError on non-2xx
export function subscribeLastRequest(cb: (r: LastRequest) => void): () => void; // for UI-G-4 (D3)
```

- `api/queries.ts` holds TanStack Query hooks: `useHealth()` (refetch every 10 s), `useDemoConfig()`, `useFixtures(filters)`, `useFixture(id)`, `useCompare(module, input)`. `useCompare` is a `useQuery` keyed by `[module, fixtureId ?? hash(resource), thresholds]`, with `placeholderData: keepPreviousData`, so slider changes don't flash an empty state.

**Step 4 — Design tokens (`index.css`):** CSS custom properties on `:root`, a dark variant under `@media (prefers-color-scheme: dark)`, and Tailwind referencing the variables.
- Decision colours: `--c-accept` (green), `--c-review` (amber), `--c-flag` (red), `--c-neutral` (grey), `--c-mock` (amber badge), `--c-live` (green badge).
- Always pair colour with an icon and text (UI-G-6, UI-NFR-4).
- Font: bundled `@fontsource-variable/inter`, with **no CDN** (UI-NFR-3).
- Font scale: `html[data-scale="125"] { font-size: 125%; }`.

**Step 5 — Noul display helper (`lib/noul.ts`, UI-G-1b):**

```ts
export interface NoulView { answer: boolean; pTrue: number; confidence: number; label: string }
export function noulView(pTrue: number): NoulView; // answer = p >= 0.5; confidence = max(p, 1-p); label "✓ 94%" / "✗ 92%"
```

**Step 6 — Shell components:**
- `ModeBadge`: `MOCK` or `LIVE · {jev_model}`, from `useHealth()`. The mock tooltip has the exact text from UI-G-1.
- `HealthDot`: green/red; a red state shows a retry banner.
- `ErrorCard` (UI-G-5): shows `error`, `detail` and `request_id`, plus a "copy request id" button. Used by every page for `ApiError`.
- `TopBar`: title, nav tabs, ModeBadge, HealthDot, and slots for the scene stepper (D4) and the drawer toggle (D3).

**Step 7 — Overview page (UI-O-1…3):**
- `ArchitectureDiagram` is inline SVG: FHIR JSON → Serializer → Jev (Choice/Score/Noul) → Decision → Action. It has a CSS dash animation on the edges and a dimmed "LLM reasoning layer · next" branch. It respects `prefers-reduced-motion`.
- Three `ModuleCard`s show the primitive and the latest benchmark accuracy and p95 from `GET /api/v1/demo/benchmarks` → latest report (or "no report"), linking to Studio.
- A "Start demo" button → `/studio/quality`.

**Step 8 — Studio page (UI-S-1…7).** Layout is three columns at ≥ 1024 px and stacked below.

| Component | Props (contract) | Behaviour |
| --- | --- | --- |
| `FixturePicker` | `{ module, value: string \| null, onChange(id) }` | Grouped by source, search box, shows `label` and a `hard` tag; unapproved labels shown with a "draft" marker |
| `JsonView` | `{ value: unknown, collapsedDepth?: number }` | Read-only tree |
| `FlatStateTable` | `{ state: Record<string, unknown> }` | Booleans as ✓/✗ chips; `null` rows in amber |
| `QuestionBox` | `{ questions: string[] }` | The exact constants from `DemoConfig.questions` for this module |
| `DecisionCard` | `{ data: CompareResponse }` | Switches on `module` → `QualityDecision` / `RouterDecision` / `NotifiableDecision` |
| `ScoreGauge` | `{ score, threshold, confidence }` | 0–100 radial gauge with a threshold tick |
| `LevelDistribution` | `{ levels: Record<string, number> \| null }` | Live mode only (hidden when null or mock) |
| `ProbabilityBars` | `{ probabilities, winner, floor, overridden }` | 5 bars, a dashed floor line, and the note "overridden: confidence X < Y" |
| `NoulMeter` | `{ pTrue, reviewBand: [lo, hi] }` | 0–1 axis with shaded not/review/confirmed bands, using `noulView` for the label |
| `DinkesCard` | `{ disease, urgency }` | Only when `lane === "flagged"` |
| `ThresholdSliders` | `{ module, value: Thresholds, onChange }` | Only the sliders relevant to the module; parent debounces 250 ms |
| `VerdictStrip` | `{ verdict, jevDecision, ruleDecision, groundTruth }` | Three pills with ✓/✗; hidden when `ground_truth` is null |
| `ArtifactTabs` | `{ response, flag, auditEvent }` | JSON tabs with copy; Flag tab only when present |
| `LatencyLine` | `{ jevMs, e2eMs, mock }` | Says "simulated" in mock mode |

- Studio state lives in the URL: `/studio/:module?fixture=<id>`. Thresholds are local state initialised from `DemoConfig.thresholds`; resetting restores the defaults.
- Changing the fixture or a threshold re-runs `useCompare`. The decision card animates value changes (CSS transitions only).
- Notifiable urgency comes from the fixture label or disease data. If it's unavailable, show "mandatory reporting" without an urgency.

**Step 9 — Playground page (UI-PL-1…3):** module selector, a CodeMirror JSON editor (JSON lint), "load fixture as starting point", and Run → `POST /compare/{module}` without `fixture_id`. A 422 renders `ErrorCard` with the detail. There's no verdict strip.

**Step 10 — Makefile:**

```make
web-install:  cd web && npm ci
web-dev:      cd web && npm run dev
web-build:    cd web && npm run build
web-types:    python scripts/dump_openapi.py && cd web && npm run types
demo:         $(MAKE) web-build && DEMO_ENABLED=true uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000
web-test:     cd web && npm run lint && npm run typecheck && npm run test
web-e2e:      cd web && npm run e2e
```

**Step 11 — Tests:**
- **Vitest (unit):**
  - `noulView` boundaries: 0, 0.5, 1, 0.08, 0.94.
  - `ErrorCard` shows the request id.
  - `VerdictStrip` hides without ground truth.
  - `ProbabilityBars` shows the override note.
  - `DecisionCard` renders all three modules from **recorded responses** in `web/src/test/fixtures/compare_{quality,router,notifiable}.json`. `scripts/dump_openapi.py --samples` writes them: it runs `Comparer.compare` with `MockJevClient` on `complete_patient`, `mixed_bundle` (floor 0.99) and `japanese_encephalitis_a83`. `make web-types` also refreshes them, and the files are committed.
- **Playwright (e2e):**
  - `playwright.config.ts` `webServer` runs `make web-build`, then `DEMO_ENABLED=true MOCK_JEV=true uvicorn jev_fhir.main:app --port 8010`, with `baseURL http://127.0.0.1:8010/demo/`.
  - Specs:
    1. Overview loads, and the mode badge says MOCK.
    2. Studio quality: pick `complete_patient`, see `auto_accept`, drag the threshold to 85, see `review_needed`.
    3. Studio router: `mixed_bundle`, floor 0.99, see the override note.
    4. Studio notifiable: the JE fixture shows the Flag tab and the Dinkes card; common cold shows neither.
    5. Playground: an invalid Condition shows the ErrorCard with a request id.
    6. A deep link reload of `/demo/studio/router?fixture=…` works.
  - Screenshots at 1280×720 and 1920×1080 go to `web/e2e/screenshots/` (git-ignored).
  - A network guard fails the test if any request goes to a host other than `127.0.0.1` (UI-NFR-3).

### Codex Evaluation Checklist

```
☐ node --version → v20.x; npm ci succeeds from a clean clone (rm -rf web/node_modules first)
☐ make web-test → eslint 0 errors, tsc 0 errors, vitest all pass
☐ make web-types then git diff --exit-code web/src/api/schema.d.ts → no diff (types in sync with backend)
☐ grep -rn "interface CompareResponse\|type CompareResponse =" web/src --exclude=schema.d.ts → only re-exports in types.ts
☐ make web-build → web/dist/index.html exists; no files > 1 MB except sourcemaps
☐ make demo → curl -s :8000/demo | grep -c "<div id=\"root\">" → 1; curl :8000/demo/studio/quality → index.html (SPA fallback)
☐ make web-e2e → all 6 specs pass; screenshots produced at both sizes (list files)
☐ Network guard spec passes (no non-localhost requests)
☐ grep -rn "http://\|https://" web/src --exclude=schema.d.ts → no external URLs (fonts bundled)
☐ Mode badge tooltip text equals UI-G-1 wording exactly
☐ Noul labels use noulView everywhere (grep NoulMeter + QualityDecision use it)
☐ Colour never the sole signal: DecisionCard lanes render icon + text (cite component)
☐ localStorage access wrapped in try/catch (grep)
☐ Backend make test still green (no backend regressions)
```

### Evaluation Record

```
Evaluated: <date> by <session>
Screenshots: <paths>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL
```

---

## Phase D3: Live Pipeline & Observability Drawer

**Depends on:** D2 PASS.
**Requirement refs:** UI-P-1…7, UI-G-4, Demo Plan §5 D3 live-mode constraints.

### Codex Implementation

**Goal:** the "hub under load" screen streaming real decisions over SSE, plus the observability drawer.

**Step 1 — SSE hook (`api/sse.ts`):**

```ts
export type StreamEvent =
  | { kind: "decision"; seq: number; data: DecisionEvent }
  | { kind: "run"; seq: number; data: RunEvent };

export function useDecisionStream(onEvent: (e: StreamEvent) => void): { connected: boolean };
```

- Use native `EventSource("/api/v1/demo/decisions/stream")` with listeners for `decision` and `run`. The browser resends `Last-Event-ID` on reconnect, and the backend replays from there.
- Close on unmount. `connected` reflects `onopen` and `onerror`.

**Step 2 — Pipeline state (`pages/pipeline/reducer.ts`, a pure reducer):**

```ts
interface RunSummary { runId: string; total: number; processed: number; status: "running" | "finished" | "stopped";
  lanes: Record<Lane, number>; routedByCategory: Record<string, number>; agreement: { correct: number; judged: number };
  tokens: number; errors: number }
interface PipelineState { current: RunSummary | null; previous: RunSummary | null;
  events: DecisionEvent[];            // current run, newest first, capped at 500
  latencies: number[];                // last 50 jev_latency_ms
  confidences: number[] }             // current run
type Action = { type: "event"; event: StreamEvent } | { type: "reset" };
```

- Events with a `run_id` other than `current.runId` are ignored, apart from a `run: started` event, which moves `current` to `previous` and starts fresh.
- `run: finished` or `run: stopped` sets the status.

**Step 3 — Pipeline page components (UI-P-1…7):**

| Component | Contract |
| --- | --- |
| `RunControls` | source select, pace (1 / 4 / 10 / max), `ThresholdSliders` (all modules), Start / Stop / Reset. Start → `POST /pipeline/run`; Stop → `POST /pipeline/{id}/stop` |
| `StatsStrip` | processed/total, throughput (events per s over the last 5 s), p50/p95 of `latencies`, agreement %, tokens (+ cost at $42/1e9 in live mode) |
| `LaneBoard` | four columns with counters; Routed shows sub-counts per category; each column lists its last 8 items |
| `LiveFeed` | table (time, ref, module, decision, confidence bar, latency, lane chip); a row click → `/studio/{module}?fixture={fixture_id}` |
| `LatencySparkline` | Recharts line of the last 50 latencies |
| `ConfidenceHistogram` | 10 buckets, stacked by module |
| `ReviewQueue` | review-lane items with `lane_reason`; Accept / Override buttons change **client state only**, labelled "simulated reviewer" |
| `RerunDelta` | when `previous` exists: "Review queue: {prev} → {curr} (Δ ±n)" |

Performance (UI-NFR-1): the feed renders at most 100 rows (virtualise or slice), and chart updates are throttled with `requestAnimationFrame`.

**Step 4 — Observability drawer (UI-G-4):** a slide-over toggled from the TopBar (and by the `O` key in D4).
- Last 50 decisions from `GET /decisions` plus live stream updates, as JSON lines.
- The last request's `X-Request-Id` and `X-Request-Duration-Ms`, from `subscribeLastRequest`.
- A metrics summary: fetch `/api/v1/metrics` every 5 s while open, parse the `jev_fhir_decisions_total{module,decision}` and `jev_fhir_http_requests_total` lines into tables, with a toggle to show the raw text.

```ts
export function parsePrometheus(text: string): Array<{ name: string; labels: Record<string, string>; value: number }>;
```

**Step 5 — Tests:**
- **Vitest:**
  - Reducer: `started` → decisions → `finished`; lane counts sum to `processed`; foreign `run_id` ignored; `previous` kept on a new start; the event cap is 500.
  - `parsePrometheus` on a captured metrics sample.
  - `RerunDelta` shows the sign.
- **Playwright:**
  1. Start with source unit and pace max; wait for "finished"; the four lane counters sum to `total` from the start response.
  2. Stop mid-run at pace 1/s → status "stopped", and processed < total.
  3. Re-run with quality threshold 95 → the RerunDelta review count increases.
  4. Clicking a review item shows its `lane_reason`.
  5. The drawer opens and shows a request id and a parsed metrics table.
  6. No console errors during a full run.

### Codex Evaluation Checklist

```
☐ make web-test green; make test (backend) green
☐ make web-e2e → all D2 + D3 specs pass
☐ Lanes + counters sum to total for a full unit run (cite e2e assertion)
☐ Stop leaves no running task: after stop, GET /decisions?limit=1 seq stable for 3 s (curl twice)
☐ Two browser tabs on /demo/pipeline both receive events (manual or e2e with two pages)
☐ Kill + restart uvicorn during a run → page shows disconnected, then reconnects without reload
☐ Feed never renders > 100 rows (inspect DOM count in e2e)
☐ Review items show exact lane_reason strings from the D1 table
☐ Drawer shows X-Request-Id matching the last response header
☐ No console errors / unhandled promise rejections in e2e logs
```

### Evaluation Record

```
Evaluated: <date> by <session>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL
```

---

## Phase D4: Benchmarks, Presenter Mode, Polish, Rehearsal

**Depends on:** D3 PASS; for the final rehearsal, D0.5's live full report must exist.
**Requirement refs:** UI-B-1…8 (UI-B-8 out of scope), UI-D-1…3, UI-NFR-*, Demo Plan §2 and §6.

### Codex Implementation

**Goal:** the evidence screen, the one-key scene presets, and a rehearsed, offline-safe demo.

**Step 1 — PRD targets (`lib/prdTargets.ts`):**

```ts
export const PRD_TARGETS = {
  quality_scorer:      { metric: "jev_accuracy", min: 0.85, label: "Action agreement ≥ 85%" },
  bundle_router:       { metric: "jev_accuracy", min: 0.90, label: "Routing accuracy ≥ 90%" },
  notifiable_detector: { recallMin: 0.95, precisionMin: 0.80, label: "Recall ≥ 95%, precision ≥ 80%" },
  latency:             { p50MaxMs: 30, p95MaxMs: 100 },
} as const;
```

**Step 2 — Benchmarks page (UI-B-1…7b):**

| Component | Contract |
| --- | --- |
| `ReportSelector` | `GET /benchmarks`; newest first; shows the mode badge (mock/live), dataset and model |
| `AccuracyTable` | module × (Jev, Rules) + a PRD target chip (PASS green / FAIL red, never hidden) |
| `BreakdownTable` | per source and per difficulty (from `breakdown`); present only for `dataset=full` reports |
| `LatencyPanel` | mean/p50/p95 per module against PRD lines |
| `CalibrationChart` | per bucket: mean confidence vs observed accuracy, with the y = x reference line |
| `DisagreementList` | rows where `jev_correct !== rule_correct` or both are false; click → Studio with that fixture |
| `NotifiablePRF` | Jev vs rules precision/recall/F1 |
| `MockDisclaimer` | when `mode === "mock_jev"`, the exact text from UI-B-7 |
| `LiveMeta` | when live: model, timestamp, tokens, cost |
| `LabelGuard` | when `quality_labels_banded !== true`: replace the quality accuracy with "labels not suitable for live scoring" |
| `LiveVsMock` | when the latest live and latest mock reports for the same dataset both exist, side-by-side accuracy columns |

A warning banner appears when `unapproved_labels > 0`.

**Step 3 — Scenes (`src/scenes.ts`, UI-D-1):**

```ts
export interface Scene {
  id: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  title: string;
  route: string;                                  // e.g. "/studio/quality"
  fixtureId?: string;                             // must exist in GET /fixtures
  thresholds?: Partial<Thresholds>;
  autoAction?: "startPipeline";
  pipeline?: { source: string; ratePerS: number | null };
  note: string;                                   // talk track (Demo Plan §2)
  steps?: Array<{ fixtureId?: string; thresholds?: Partial<Thresholds>; note: string }>; // sub-steps within a scene
}
export const SCENES: Scene[];
```

- Scenes follow the Demo Plan §2 flow. Sub-steps (e.g. Scene 1 → `invalid_nik` → dotted NIK → threshold 85) advance with `→` before the next scene.
- **Fixture choices come from the D0.5 live full report**: the fixtures that show each point most clearly. Record why each was chosen in a comment.

**Step 4 — Presenter controls (UI-D-2, UI-D-3):**
- A global key handler, ignored while focus is in an input or editor:
  - `←` / `→`: step or scene
  - `1`–`6`: jump to a scene
  - `R`: reset the scene
  - `F`: font scale 100 ↔ 125
  - `O`: drawer
  - `N`: presenter notes
- A `SceneStepper` in the TopBar shows `Scene n/6 · step m/k`.
- A notes strip at the bottom shows `note` (off by default; the preference persists in localStorage wrapped in try/catch).
- A scene change navigates, sets the fixture and thresholds, and runs `autoAction`.

**Step 5 — Polish (UI-NFR-*):**
- Check layout at 1280×720 and 1920×1080, with no horizontal scroll.
- Check WCAG AA contrast for the decision colours in light and dark modes.
- Honour `prefers-reduced-motion`.
- The empty states read "no report yet" and "no fixtures match".
- Every `ApiError` path shows `ErrorCard`.

**Step 6 — Rehearsal script (`docs/demo-runbook.md`):** a one-page checklist from Demo Plan §6. It covers the cold start (`make demo`), the mode switch, the fallback (restart with `MOCK_JEV=true` in < 30 s), per-scene key presses and expected screens, and the Q&A answers.

**Step 7 — Tests:**
- **Vitest:**
  - Every `SCENES[*].fixtureId` and step fixture exists in a committed catalog snapshot (`web/src/test/fixtures/catalog.json`, refreshed by `make web-types`).
  - `LabelGuard` hides quality accuracy for unbanded reports.
  - The PRD chip shows FAIL for 0.733 routing.
  - The key handler ignores keystrokes inside inputs.
- **Playwright:**
  1. The benchmarks page shows the latest report; the mock report shows the disclaimer and router FAIL.
  2. A disagreement row click opens Studio with that fixture.
  3. Pressing `→` from Overview walks scenes 0 through 6 with no manual input, and each scene's key element is visible.
  4. `R` resets the thresholds.
  5. `F` changes the root font size.
  6. The network guard (no external hosts) covers the whole walk.

**Step 8 — Manual (Budi):**
- Two full dry runs from a cold `make demo`, one **live** and one **mock**, each ≤ 13 minutes.
- Record problems in the Evaluation Record, and re-pick scene fixtures if live results changed.

### Codex Evaluation Checklist

```
☐ make web-test, make web-e2e, make test all green
☐ Benchmarks: mock report shows MockDisclaimer text verbatim; router chip FAIL at 0.733
☐ Live report (from D0.5) shows model, tokens, cost; LiveVsMock renders when both exist
☐ Full-dataset report shows BreakdownTable by source and difficulty; unit report hides it
☐ LabelGuard triggers on a pre-D0 report (copy an old bench_*.json into a temp results dir)
☐ Scene walk e2e passes: scenes 0–6 + sub-steps reachable by → only
☐ Scene fixture ids all exist in the catalog (vitest)
☐ Scene fixtures chosen from the live full report (comment in scenes.ts cites the report name)
☐ Key handler ignores keys typed in Playground editor (e2e or vitest)
☐ Layout: no horizontal scroll at 1280×720 (e2e evaluates document.scrollWidth <= innerWidth)
☐ Contrast: decision colours meet 4.5:1 on background in both themes (list computed ratios)
☐ docs/demo-runbook.md exists and matches the current scenes
☐ (manual, Budi) live dry run ≤ 13 min — time: ____ ; mock dry run ≤ 13 min — time: ____
☐ (manual, Budi) fallback drill: kill live server, restart MOCK_JEV=true, back on scene in < 30 s
```

### Evaluation Record

```
Evaluated: <date> by <session>
Dry runs:  live <mm:ss>, mock <mm:ss>
Results:   <checklist with evidence>
Verdict:   PASS | FAIL — demo ready?
```

---

## Appendix A: Makefile Targets by Phase

| Target | Phase | Command |
| --- | --- | --- |
| `bench-live` | D0 | `MOCK_JEV=false python -m benchmarks.bench_runner --live` |
| `smoke-live` | D0 | `MOCK_JEV=false python scripts/smoke_live.py` |
| `dataset` | D0.5 | `python scripts/generate_dataset.py --seed 42` |
| `bench-full` | D0.5 | `MOCK_JEV=true python -m benchmarks.bench_runner --dataset full` |
| `bench-live-full` | D0.5 | `MOCK_JEV=false python -m benchmarks.bench_runner --live --dataset full` |
| `web-install` / `web-dev` / `web-build` / `web-types` / `web-test` / `web-e2e` | D2 | see D2 Step 10 |
| `demo` | D2 | `web-build` + serve with `DEMO_ENABLED=true` |

## Appendix B: Findings → Phase Map

| Finding (Demo Plan §1.3) | Fixed in |
| --- | --- |
| F1 quality labels fitted to mock | D0 Step 10 |
| F2 benchmark mock-only | D0 Step 11 |
| F3 Noul probability semantics | D0 Step 6 |
| F4 no timeout/retry config | D0 Step 3 |
| F5 errors collapsed to 502 | D0 Steps 2, 4 |
| F6 model hard-coded | D0 Steps 1, 3, 4 |
| F7 threshold settings unused | D0 Step 5 |
| F8 Jev detail dropped | D0 Step 7, D1 `jev_raw` |
| F9 README / key | Done Sep 24 (rotation: Budi) |
| F10 fixtures too small and easy | D0.5 |
| F11 FHIR R5 models used as "R4" | ✅ Done Sep 24 (D0 Step 9) |
