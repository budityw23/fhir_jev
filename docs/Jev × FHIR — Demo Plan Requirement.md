# Jev × FHIR — Demo Plan & UI Requirements

Sep 24, 2026 · @budi · **Rev 2** (Sep 24, 2026): re-planned after a code evaluation; see §1 and the "Rev 2" notes in §4, §5 and §7 · **Rev 3** (Sep 24, 2026): added the benchmark dataset phase D0.5 (finding F10)

## Purpose

Phases 1–5 produced a working decision layer: three modules, an API, and a benchmark harness. All of it lives in JSON and a terminal. This doc covers the **Demo UI**, a web interface that shows the whole story in about 12 minutes: FHIR data comes in, Jev decides, the confidence threshold changes what happens next, and the benchmarks show where Jev wins and where it loses.

The doc has four parts:

1. **Demo scenario**: the story, scene by scene, with talk track
2. **UI requirements**: screens, components, behaviour
3. **Demo API requirements**: backend additions the UI needs
4. **Implementation phases**: same Codex-builds → Claude Code-evaluates workflow as the Phases doc

**Design principle:** the UI must never make the demo look better than the evidence. Mock mode is labelled everywhere, and where rule baselines beat Jev, the UI shows it plainly.

---

## 1. Current State: Code Evaluation (Sep 24, 2026)

### 1.1 Health Check

```
✅ make lint       — ruff check + format clean (43 files)
✅ make typecheck  — mypy --strict clean (40 source files)
✅ make test       — 48 passed, 3.55s (was 43 at Phase 5)
✅ coverage        — 97% overall (was 93%); every route and module at 98–100%
⚠️ 151 warnings    — fhir.resources `parse_obj` deprecation (library internals, cosmetic)
❌ no web/, no demo routes, no demo settings — demo work has not started
```

### 1.2 What Changed Since Rev 1

`LiveJevClient` has been **rewritten on the official `typesafe-sdk` (0.7.x)** in place of hand-rolled httpx calls. The changes:

- All three primitives go through `AsyncTypeSafeClient.system_one()` with typed `Choice` / `Score` / `Noul` questions.
- Score uses a **10-level rubric** (`_QUALITY_LEVELS`), and the SDK's level index is mapped back to 0–100.
- `tokens_used` now comes from real SDK `usage` (input + output tokens).
- SDK errors are wrapped as `JevClientError` → HTTP 502. The old `httpx.TimeoutException` handler and the `httpx` runtime dependency were removed.
- `JEV_BASE_URL` now defaults to `https://api.typesafe.ai`, and the legacy `/v1/` suffix is stripped.
- Six new tests cover the live client against a mocked SDK.

**Impact on the demo:** a **live Jev demo is now realistic**. Rev 1 treated mock mode as the likely default; Rev 2 makes live mode the primary target, with mock as the fallback. That exposes the issues below, which only matter once real Jev answers come back.

### 1.3 Findings That Affect the Demo

| # | Severity | Finding | Why it matters for the demo |
| --- | --- | --- | --- |
| F1 | 🔴 High | **Quality ground truth is fitted to the mock's formula.** All 20 labels in `ground_truth/quality_scores.json` are single points (`[80,80]`, `[60,60]` …) equal to `field_completeness × 10`, which is exactly how `MockJevClient.score()` computes its score. | Real Jev will almost never hit an exact point, so a live benchmark would report ~0% quality accuracy **because of the labels, not the model**. The Benchmarks screen would be meaningless. |
| F2 | 🔴 High | **The benchmark runner is hard-coded to `MockJevClient`** (`bench_runner.py:102`), with `mode: "mock_jev"` and `tokens_used: 0` written as constants. | There is no way to produce the live evidence Scene 5 needs. |
| F3 | 🟠 Medium | **Noul `probability` means different things in mock and live.** Live: `probability = P(statement is true)`. Mock NIK path: `probability = confidence in the answer` (0.92 when the answer is *false*). Mock notifiable path uses P(true) (0.1 when false). | The NIK gate would read "✗ 0.92" in mock and "✗ 0.08" in live for the same fact. The UI can't render one consistent meter. |
| F4 | 🟠 Medium | **No explicit timeout or retry for live calls.** The SDK defaults are a 10 s request timeout plus `RetryPolicy(max_retries=2, timeout=30s)`. Phase 1 specified 5 s and 2 retries. | A single hung call can freeze a Studio click for up to ~30 s on stage. |
| F5 | 🟠 Medium | **All SDK errors collapse to `502 jev_error` / "Jev SDK request failed".** Timeout, rate limit (429) and bad key (401) all look the same. | On demo day you can't tell "wrong key" from "API slow" from the UI error card. |
| F6 | 🟡 Low | **Model is hard-coded `jev-latest`** (`LiveJevClient._MODEL`). PRD NFR-5 asks for a pinned version. | The mode badge can't state which model produced a result, and results can drift between rehearsal and demo. |
| F7 | 🟡 Low | **`quality_threshold_default`, `route_confidence_minimum`, `notifiable_confidence_minimum` in `config.py` are never read.** Routes and modules use their own literal defaults. | Demo sliders need one source of default thresholds. |
| F8 | 🟡 Low | **Module responses drop Jev detail:** `tokens_used`, Score `level_probabilities` and the raw Noul probability are not in the API responses. | The cost card and the "score distribution" view need them. |
| F9 | ✅ Resolved Sep 24 | README `detect-notifiable` curl returned 422; `.env.example` held the real API key. | README rewritten with verified examples; key moved to git-ignored `.env`. Key rotation still pending (Budi). |
| F11 | ✅ Resolved Sep 24 | Validation targeted **FHIR R5, not R4**: the `fhir.resources` 8.x top-level models are FHIR 5.0.0. | Switched to `fhir.resources.R4B` (identical to R4 for the resources used; cross-checked against the official HL7 R4 4.0.1 JSON schema). Fixed the R5-shaped AuditEvent and 3 R5-only bundle fixtures. All 50 fixtures and the generated Flag/AuditEvent are now valid R4. |
| F10 | 🔴 High (added Rev 3) | **The fixture set is too small and too easy to tell Jev apart from rules.** Details below. | See the list after this table. |

**F10 details:**
- All 9 notifiable Conditions use the exact ICD-10 codes in `data/notifiable_diseases.json`, and the rule baseline is an exact-code lookup against that list. The one SNOMED fixture (22298006, myocardial infarction) isn't notifiable. Nothing is coded differently from the list, so on this data Jev can at best tie the rules.
- Counts are below the PRD's own benchmark sizes: 20 quality resources against a target of 50, and 15 bundles against 100. Routing has 1–2 examples in some categories (`encounter_summary`: 1).
- `tests/fixtures/observations/` is **empty**, so the Observation quality path has no data.
- 13 of 15 bundles have 0–2 entries, and `large_bundle` is 50 copies of the same kind of Observation. None looks like a real clinic submission.
- Patient cases only test *missing* fields. There are none with a field that is present but wrong (a NIK with dots, a placeholder name, a future birth date).

The data is fine for unit tests, and it met the Phase 5 target. It can't produce meaningful benchmark evidence or demo presets. **Phase D0.5** fixes this.

**Not verified:** no live call was made during this evaluation, so whether the key works and what real latency, accuracy and probabilities look like is still unknown. Phase D0 ends with a live smoke test for this reason.

### 1.4 What the UI Can Use Today

| Capability | Exists? | Where |
| --- | --- | --- |
| Quality score (Patient / Observation) with threshold | ✅ | `POST /api/v1/quality-score` |
| Bundle routing with probabilities | ✅ | `POST /api/v1/route-bundle` |
| Notifiable detection + FHIR Flag | ✅ | `POST /api/v1/detect-notifiable` |
| Health + mock/live mode | ✅ | `GET /health` |
| Live Jev via official SDK | ✅ new (untested against the real API) | `jev_client/client.py` |
| Prometheus metrics | ✅ | `GET /api/v1/metrics` |
| Request ID + duration headers | ✅ | `X-Request-Id`, `X-Request-Duration-Ms` |
| 50 labelled fixtures (20 patients, 15 conditions, 15 bundles) | ✅ (quality labels need rework, F1) | `tests/fixtures/`, `benchmarks/ground_truth/` |
| Benchmark reports (JSON + MD) | ✅ mock only (F2) | `benchmarks/results/bench_*.json` |
| AuditEvent builder | ✅ (not exposed via API) | `fhir_helpers/audit_event.py` |

**Gaps the demo must close** (details in §4):

- No endpoint to **list or load fixtures**, so the UI can't offer a picker.
- No way to see **what Jev actually receives**. The serialized flat state is the most important "aha" in the demo, and it stays internal today.
- **Rule baselines** live in `benchmarks/baselines/` and can't be called from the API, so there is no live side-by-side comparison.
- Router and notifiable **thresholds are method params only**; the API doesn't expose them. The "confidence is the control knob" message needs them.
- **Decisions only go to stdout** (structlog). There is no in-memory feed for a live dashboard.
- **No batch or stream** mode to simulate an ingestion hub.
- **No CORS or static serving** for a frontend.

**Known facts that shape the demo:**

- The mock client is effectively rule-driven (`mock.py` keys off `contains_lab_codes`, the ICD-10 code set, and NIK length). **In mock mode, "Jev vs rules" is not a real comparison.** The UI must say so.
- Mock bundle routing scored **0.733 vs rules 0.933**. It misroutes `empty_bundle`, `patient_bundle`, `nested_bundle` and `mixed_bundle`, because the mock's fallback confidence (0.60–0.95) never drops below the 0.5 override. That misses both the PRD target (≥ 90%) and UC-2 ("ambiguous → `unknown`"). This is a **mock artefact**. The live result is unknown until D0's live benchmark runs.
- Every expected value in the Rev 1 scene scripts (score 80, `lab_result` 0.92, probability 0.95) is a **mock value**. In live mode the scenes must be driven by what Jev actually returns. D0's live smoke test and D4's rehearsal decide which fixtures make the best presets.
- The README `detect-notifiable` curl was fixed on Sep 24 and verified to return 200.
- Rev 3: scene presets and the Studio fixture picker will draw on the **D0.5 benchmark dataset**, not only the 50 unit-test fixtures (F10).

---

## 2. Demo Scenario

### Setting

> **"A provincial health data hub, Tuesday morning."**
> Clinics across the province push FHIR R4 data to a SPHERES-like hub. Before anything reaches analytics or public-health surveillance, three decisions happen on every resource: *Is this data good enough? Where does this Bundle go? Must this Condition be reported to Dinkes?* Today those are brittle rules or slow LLM calls. Jev makes them in tens of milliseconds, with a confidence value you can act on.

**Audience:** technical interviewers, engineering leads, health-informatics peers. **Length:** ~12 min plus Q&A. **Mode (Rev 2):** **live Jev is the primary mode**, now that the SDK client exists. Mock is the fallback if the API is unavailable on the day, clearly labelled. Rehearse both.

### Scene Flow

| # | Scene | Screen | Time | Key message |
| --- | --- | --- | --- | --- |
| 0 | The problem & architecture | Overview | 1.5 min | Decision layer between the FHIR server and workflows; three primitives, three modules |
| 1 | Quality gate | Studio → Quality | 2 min | Score + NIK gate; the **threshold slider** decides auto-accept vs. review |
| 2 | Bundle routing | Studio → Router | 2 min | Probabilities, not just labels; low confidence → `unknown` → human |
| 3 | Notifiable disease → Flag | Studio → Notifiable | 2 min | Positive detection produces a **real FHIR Flag** plus an AuditEvent |
| 4 | Hub under load | Live Pipeline | 2.5 min | 50 resources stream through; lanes fill; review queue shows where humans are needed |
| 5 | Evidence | Benchmarks | 1.5 min | Accuracy vs. PRD targets, latency, calibration, **where Jev lost** |
| 6 | What's next | Overview (architecture) | 0.5 min | Low-confidence → LLM reasoning layer (two-layer architecture) |

### Scene Scripts

Each scene is a **preset** in the UI (§3.7). The presenter presses `→` and the right screen, fixture and settings load, so nothing gets typed live.

**Scene 0 — Overview**
- Show the architecture diagram, animated: FHIR JSON → serializer → Jev (Choice / Score / Noul) → action.
- Point at the **mode badge** (`MOCK` / `LIVE · Jev v1.x`) and the health indicator.
- Talk track: *"Most clinical software is a giant decision tree. Rules are brittle, LLMs are slow and expensive. Jev sits in the gap: typed decisions with probabilities, no text generation."*

**Scene 1 — Quality gate** (`patients/complete_patient.json` → `invalid_nik.json` → `minimal_patient.json`)
1. Load `complete_patient`. Show the raw FHIR on the left and the **"What Jev sees"** flat state in the middle (`has_identifier: true`, `identifier_value_length: 16`, `field_completeness: 8/10`, …). Decision: **auto-accept, NIK valid**. The score is 80 in mock mode; in live mode, show whatever Jev returns, plus the 10-level score distribution (F8).
2. Switch to `invalid_nik` (15-digit NIK). The NIK gate flips to **false**. *"A yes/no primitive used as a validation gate."* Rev 3: then load the D0.5 **dotted NIK** (`3173.0101.0190.0001`), which a length rule rejects even though it's a real ID written differently. Show Jev's answer against the rule's.
3. Switch to `minimal_patient`. Low score, **review needed**, missing fields listed.
4. **The control knob:** reload `complete_patient` and drag the threshold 70 → 85. The same resource flips to **review needed**. *"The confidence threshold is the product decision: lower means more automation, higher means more human review."*

**Scene 2 — Bundle routing** (`lab_bundle` → `immunization_bundle` → `mixed_bundle`)
1. `lab_bundle` → `lab_result` with a probability bar chart across all 5 categories.
2. `immunization_bundle` → `immunization_report`.
3. `mixed_bundle`: show **Jev vs. rules vs. ground truth**. Ground truth is `unknown`. In mock mode Jev says `lab_result` and rules say `encounter_summary`, so **both are wrong**. In live mode, use whatever Jev returns: if live Jev gets it right where rules don't, that is the strongest moment of the demo. *"This is the case that matters: ambiguous input. Next is the confidence floor that sends it to a human."* Then drag the router's minimum confidence up and watch it drop to `unknown`.

**Scene 3 — Notifiable disease** (`japanese_encephalitis_a83` → `common_cold_j06` → `snomed_only`)
1. JE A83.0 → **confirmed notifiable**, probability shown. A red "Report to Dinkes within 24h" card appears, and the **FHIR Flag** tab shows the generated resource (SNOMED 281269004, subject reference, period) plus the **AuditEvent**.
2. Common cold J06.9 → not notifiable, no Flag.
3. Rev 3, the hard case: a **text-only "Demam berdarah dengue (DBD)"** Condition or a **SNOMED-coded dengue** Condition from the D0.5 hard set. The rules see no ICD-10 code and say "not notifiable"; show what Jev says, live. This is the case where a learned model *should* help. Report the result honestly either way. (Rev 1 used `snomed_only`, but that fixture is a myocardial infarction and correctly not notifiable, so it proved nothing.)

**Scene 4 — Hub under load**
1. Press **Start ingestion**. All 50 fixtures stream through their module at a watchable pace (e.g. 4/s).
2. The live feed scrolls; four lanes fill: **Auto-accepted**, **Routed** (per category), **Flagged → Dinkes**, **Review queue**.
3. Counters, latency sparkline (p50/p95), confidence histogram.
4. Stop, then drag a global threshold and **re-run**. The review-queue count changes visibly. That makes the control knob concrete at scale.
5. Open one review-queue item to show why it landed there (low confidence / below threshold / `unknown`).

**Scene 5 — Evidence**
- Accuracy table: Jev vs. rules per module, with **PRD target chips** (pass/fail).
- Latency p50/p95 against the PRD targets (< 30 ms p50, < 100 ms p95).
- Calibration chart: stated confidence vs. observed accuracy per bucket.
- **"Where Jev lost"** list: disagreement rows from the report, with a click-through into Studio. In mock mode these are the 4 misrouted bundles; the live list is unknown until D0.
- **Live vs. mock** (Rev 2): if both reports exist, show them side by side. The mock column shows the harness works; the live column shows what Jev actually does. Add a **cost line** from real `tokens_used`.
- Talk track: *"Rules win on routing today. That's a real finding, not a failure of the demo."*

**Scene 6 — What's next**
- Back to the architecture: highlight the **low-confidence → LLM reasoning layer → human** branch (not built, shown dimmed as "next").
- Close: *"System 1 for high-volume decisions, System 2 for the long tail. The threshold decides which one runs."*

### Demo Risk Plan

| Risk | Mitigation |
| --- | --- |
| Live Jev API slow, rate-limited or down | 5 s timeout and bounded retries (D0 Step 2), so a click never hangs. Typed error card (`jev_timeout` / `jev_rate_limited` / `jev_auth`). Mode switch at startup (`MOCK_JEV`). Rehearse both. |
| Live results differ from rehearsal (`jev-latest` drift) | Pin the model if possible (Open Question 7); re-run `make bench-live` the day before and re-check scene presets. |
| Presenter types a malformed resource live | Presets only during the main flow; free-form playground only for Q&A. Validation errors render as a friendly card with `request_id`. |
| Mock results oversell Jev | Persistent `MOCK` badge + a one-line explanation on the Benchmarks screen. |
| Projector / small screen | Designed for 1280×720 minimum; presenter font scale toggle. |
| Network at venue | Everything runs on `localhost`; no CDN at runtime (fonts and assets bundled). |

---

## 3. UI Requirements

### 3.1 Tech Stack (recommendation)

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | **Vite + React 18 + TypeScript** | Component-heavy UI (JSON viewers, charts, live feed); typed API contract matches the strict-mypy backend |
| Styling | Tailwind CSS | Fast iteration, consistent tokens |
| Charts | Recharts | Probability bars, sparkline, histogram, calibration |
| JSON viewer | `@uiw/react-json-view` (read) + CodeMirror 6 (edit, playground only) | Collapsible FHIR trees |
| API types | `openapi-typescript` generated from FastAPI's `/openapi.json` | One source of truth for response models |
| Live updates | Server-Sent Events (`EventSource`) | One-way server → UI; no WebSocket dependency |
| Serving | FastAPI `StaticFiles` mounts `web/dist` at `/demo` | Single process, same origin, no CORS in demo mode |

**Lighter alternative:** Jinja2 + HTMX + Alpine.js served directly by FastAPI (no Node toolchain). Choose it if the demo UI will never grow past these screens. React is recommended here because the Studio and Pipeline screens carry a lot of client state, and the result doubles as a portfolio piece.

### 3.2 Information Architecture

```
/demo
├── Overview        (scene 0, 6)
├── Studio          (scenes 1–3)   tabs: Quality · Router · Notifiable
├── Live Pipeline   (scene 4)
├── Benchmarks      (scene 5)
└── Playground      (Q&A: paste any FHIR JSON)

Global: top bar (mode badge · health dot · scene stepper · observability drawer toggle)
```

### 3.3 Global Elements

- **UI-G-1 Mode badge:** always visible. `MOCK` (amber) or `LIVE · <model>` (green), from `GET /health`. Rev 2: `/health` also returns the configured model id (F6). Tooltip in mock mode: *"Deterministic offline client — decisions are rule-derived, latency is simulated."*
- **UI-G-1b Probability convention (Rev 2, F3):** every Noul value the UI receives is **P(statement is true)**. Meters plot P(true) on a 0–1 axis. The label shows the answer (✓/✗) and **confidence = max(p, 1−p)**, so "✗ 92% confident" reads the same in mock and live.
- **UI-G-2 Health dot:** polls `/health` every 10 s; red if unreachable, with a retry banner.
- **UI-G-3 Scene stepper:** `← Scene 2/6 →` in the top bar; keyboard `←` / `→`; loads presets (§3.7).
- **UI-G-4 Observability drawer:** slide-over with the last 50 decisions (JSON log lines), the last request's `X-Request-Id` and `X-Request-Duration-Ms`, and a parsed metrics summary from `/api/v1/metrics` with a raw-text toggle.
- **UI-G-5 Error card:** any non-2xx shows `error`, `detail`, `request_id`, never a blank screen.
- **UI-G-6 Decision colour semantics** (always paired with icon + text, colour-blind safe):
  - Auto-accept / confirmed routing → green ✓
  - Review needed / `unknown` → amber ⚠
  - Notifiable confirmed → red ⚑
  - Not notifiable / neutral → grey ○

### 3.4 Screen: Overview

- **UI-O-1** Animated architecture diagram (SVG): FHIR JSON → Serializer → Jev primitive → Decision → Action. The "LLM reasoning layer" branch is drawn dimmed and labelled *Next*.
- **UI-O-2** Three module cards (Quality / Router / Notifiable), each showing primitive (Score / Choice / Noul), latest benchmark accuracy, p95 latency, and an "Open in Studio" link.
- **UI-O-3** One-line problem statement and a "Start demo" button → Scene 1.

### 3.5 Screen: Studio (core screen)

Three-column layout, identical across the three module tabs:

```
┌──────────────────┬──────────────────────┬──────────────────────────┐
│ INPUT            │ WHAT JEV SEES        │ DECISION                 │
│ Fixture picker   │ Serialized flat state│ Decision card            │
│ (grouped, with   │ (key/value table,    │  (gauge / prob. bars /   │
│  ground-truth    │  booleans as chips,  │   yes-no + probability)  │
│  label)          │  missing = amber)    │ Threshold slider(s)      │
│ Raw FHIR JSON    │                      │ Verdict strip:           │
│ (collapsible)    │ Jev question text    │  Jev | Rules | Truth     │
│                  │ (the exact constant) │ Artifacts tabs:          │
│                  │                      │  Response · Flag ·       │
│                  │                      │  AuditEvent              │
│                  │                      │ Latency: Jev ms · e2e ms │
└──────────────────┴──────────────────────┴──────────────────────────┘
```

- **UI-S-1 Fixture picker:** grouped by type, searchable, each item tagged with its ground-truth label (e.g. `unknown`, `notifiable`, `score 80`).
- **UI-S-2 "What Jev sees":** renders `serialized_state` from the compare endpoint. Shows the exact Jev question/statement constant used (`QUALITY_SCORE_QUESTION`, `ROUTE_QUESTION`, `NOTIFIABLE_STATEMENT`, `NIK_VALIDATION_STATEMENT`) so the audience sees there is no prompt engineering.
- **UI-S-3 Decision card per module:**
  - Quality: 0–100 radial gauge with threshold marker, confidence, `level`, `action`, missing-field chips, NIK gate (✓/✗ + probability per UI-G-1b). In live mode, add a small bar chart of Score's `level_probabilities` across the 10 rubric levels, so the audience sees the model's uncertainty, not just one number.
  - Router: horizontal bars for all 5 categories, winner highlighted, dashed line at the confidence floor; if an override to `unknown` happened, a note says *"overridden: confidence 0.49 < 0.50"*.
  - Notifiable: large yes/no, probability bar with the 0.5 and 0.8 bands shaded (not / review / confirmed), status label, and a red **"Report to Dinkes · 24h"** card when confirmed (urgency from `data/notifiable_diseases.json`).
- **UI-S-4 Threshold slider(s):** Quality `threshold` (0–100); Router `confidence_minimum` (0–1); Notifiable `confirmed_threshold` / `review_threshold`. Changing a slider **re-runs the decision** (debounced 250 ms) and animates the result change.
- **UI-S-5 Verdict strip:** three pills, **Jev · Rules · Ground truth**, each ✓/✗ against ground truth. Hidden for Playground input (no ground truth).
- **UI-S-6 Artifacts tabs:** raw API response JSON; generated **Flag** (only when confirmed); generated **AuditEvent** for every decision. Each has a "copy" button.
- **UI-S-7 Latency line:** Jev call latency (labelled *simulated* in mock mode) and end-to-end `X-Request-Duration-Ms`.

### 3.6 Screen: Live Pipeline

- **UI-P-1 Controls:** Start / Pause / Reset; source (all 50 fixtures, or one type); pace (1, 4, 10 resources/s, or "max"); global thresholds (same three as Studio).
- **UI-P-2 Live feed:** newest-first table: time, resource ref, module, decision, confidence bar, latency, lane. Rows are clickable and open the item in Studio.
- **UI-P-3 Lanes board:** four columns with counters: **Auto-accepted**, **Routed** (sub-counts per category), **Flagged → Dinkes**, **Review queue**.
- **UI-P-4 Stats strip:** processed count, throughput/s, p50/p95 latency (rolling), agreement-with-ground-truth % for the run.
- **UI-P-5 Charts:** latency sparkline (last 50) and confidence histogram (10 buckets, coloured by module).
- **UI-P-6 Review queue panel:** each item shows the reason (`below threshold 70`, `confidence 0.49 < floor`, `probability in review band 0.5–0.8`). Buttons **Accept / Override** are client-side only and marked *"simulated reviewer"*.
- **UI-P-7 Re-run with new thresholds:** after changing thresholds, "Re-run" replays the same 50 fixtures; the UI shows **Δ review-queue size** against the previous run.

### 3.7 Presenter Mode & Scene Presets

- **UI-D-1** Presets live in one file (`web/src/scenes.ts`): per scene, `route`, `tab`, `fixture`, `thresholds`, and optional `autoAction` (e.g. start pipeline).
- **UI-D-2** Keyboard: `←`/`→` scene, `1`–`6` jump, `F` font-scale toggle (100% / 125%), `O` observability drawer, `R` reset current scene.
- **UI-D-3** Presenter notes: a toggleable bottom strip showing the talk-track line for the current scene (off by default).

### 3.8 Screen: Benchmarks

- **UI-B-1** Report selector: lists `benchmarks/results/bench_*.json`, latest first, with its `mode` label (mock/live) shown prominently.
- **UI-B-2** Accuracy table: module × (Jev, Rules) + PRD target chip (Quality ≥ 85%, Router ≥ 90%, Notifiable recall ≥ 95%, precision ≥ 80%). Fails shown red, never hidden.
- **UI-B-3** Latency panel: mean/p50/p95 per module vs. PRD lines (p50 < 30 ms, p95 < 100 ms).
- **UI-B-4** Calibration chart: per bucket, mean confidence vs. observed accuracy, with the diagonal as reference.
- **UI-B-5** "Where Jev lost / where rules lost": disagreement rows from the report's `rows`, each linking to Studio with that fixture.
- **UI-B-6** Notifiable P/R/F1 for Jev vs. rules.
- **UI-B-7** Mock disclaimer block, shown when `mode == "mock_jev"`: *"Mock decisions mirror rule logic; this report validates the harness, not Jev."*
- **UI-B-7b** (Rev 2) For live reports: model id, run timestamp, total tokens and estimated cost (PRD NFR-6: $42 per billion input tokens). Refuse to display quality accuracy from a report whose ground truth has single-point ranges; show *"labels not suitable for live scoring"* instead (guards against F1).
- **UI-B-8** "Run benchmark now" button (optional, see DEMO-API-7).

### 3.9 Screen: Playground

- **UI-PL-1** Module selector + CodeMirror JSON editor + "Load fixture as starting point".
- **UI-PL-2** Validate-then-run; FHIR validation errors (422) render inline with field paths.
- **UI-PL-3** Same decision card and artifacts as Studio; no verdict strip.

### 3.10 Non-Functional Requirements

- **UI-NFR-1 Performance:** Studio decision renders < 300 ms after response; Pipeline stays smooth (no dropped frames) at 10 resources/s for 50 items.
- **UI-NFR-2 Layout:** designed for 1280×720 (projector) and 1920×1080; Studio columns stack below 1024 px.
- **UI-NFR-3 Offline:** no runtime network calls except the local API; fonts and assets bundled.
- **UI-NFR-4 Accessibility:** colour never the only signal; WCAG AA contrast; all controls keyboard-reachable.
- **UI-NFR-5 Data:** synthetic fixtures only; the UI never persists resources (no localStorage for FHIR data; UI prefs only).
- **UI-NFR-6 Honesty:** mode badge on every screen; latency labelled *simulated* in mock mode; no hard-coded "impressive" numbers anywhere in the UI. Every metric comes from the API or a bench report.

---

## 4. Demo API Requirements

All new endpoints live under `/api/v1/demo/*` in a new router `routes/demo.py`, mounted only when `DEMO_ENABLED=true` (new setting, default `false`; `.env.example` sets `true`). **Existing Phase 4 endpoints and response models do not change.**

| ID | Endpoint | Purpose |
| --- | --- | --- |
| DEMO-API-1 | `GET /api/v1/demo/fixtures` | Catalog: `[{id: "patients/complete_patient.json", source, kind, module, label, difficulty, ground_truth}]`. Rev 3: merges `tests/fixtures/` (source `unit`) with the D0.5 dataset `benchmarks/dataset/` (source `hard` / `generated` / `demo`), each joined to its ground truth. Supports `?source=` and `?difficulty=` filters |
| DEMO-API-2 | `GET /api/v1/demo/fixtures/{kind}/{name}` | Raw fixture JSON. Path must resolve inside the fixtures dir (reject `..`) |
| DEMO-API-3 | `POST /api/v1/demo/compare/{module}` | Body: `{resource, resource_type?, thresholds?}`. Returns `{jev: <existing response model>, rule: {...}, ground_truth: ... \| null, serialized_state, jev_question, audit_event, override_applied}` |
| DEMO-API-4 | `GET /api/v1/demo/decisions?limit=50` | Last N decisions from an in-memory ring buffer (size 500) |
| DEMO-API-5 | `GET /api/v1/demo/decisions/stream` | SSE stream of new decisions (`event: decision`, JSON data) |
| DEMO-API-6 | `POST /api/v1/demo/pipeline/run` | Body: `{source: "all"\|"patients"\|..., rate_per_s, thresholds}`. Starts a run; results flow to DEMO-API-5 tagged with `run_id`, `lane`, `lane_reason`, `ground_truth_match`. Returns `{run_id, total}`. Plus `POST /pipeline/{run_id}/stop` |
| DEMO-API-7 | `GET /api/v1/demo/benchmarks` · `GET /api/v1/demo/benchmarks/{name}` · *(optional)* `POST /api/v1/demo/benchmarks/run` | List/read bench reports; optional on-demand run |

**Backend design notes:**

- **DEMO-BE-1 Baselines move into the package.** Move `benchmarks/baselines/*.py` → `src/jev_fhir/baselines/`, and have `benchmarks/bench_runner.py` import from there. The API can't import from the top-level `benchmarks/` directory cleanly. This is the only refactor of existing code.
- **DEMO-BE-2 Thresholds:** the modules already accept `confidence_minimum` (router) and `confirmed_threshold` / `review_threshold` (detector) as method params. The compare/pipeline endpoints pass them through; no module changes.
- **DEMO-BE-3 Serialized state:** the compare endpoint calls the module's serializer directly to return `serialized_state`. Modules stay unchanged.
- **DEMO-BE-4 Decision feed:** add `DecisionFeed` (deque + `asyncio` fan-out to SSE subscribers) to `AppServices`. The demo compare/pipeline handlers publish to it. Keep it out of `log_decision` so the core modules have no demo dependency. Optional: the three existing routes also publish, so manual curl calls show up live.
- **DEMO-BE-5 Lane assignment** (pipeline):
  - Quality: `auto_accept` → Auto-accepted; else → Review (`below threshold N`).
  - Router: category ≠ `unknown` → Routed; `unknown` → Review (`confidence X < floor` or `model chose unknown`).
  - Notifiable: `confirmed_notifiable` → Flagged; `review_needed` → Review (`probability in review band`); `not_notifiable` → Auto-accepted.
- **DEMO-BE-6 AuditEvent:** build it with the existing `AuditEventBuilder` for every compare/pipeline decision; return it, never persist it.
- **DEMO-BE-7 Static serving:** if `web/dist` exists, mount it at `/demo` with an SPA fallback to `index.html`. Redirect `/` → `/demo` when `DEMO_ENABLED`.
- **DEMO-BE-8 Dev CORS:** allow `http://localhost:5173` only when `DEMO_ENABLED` (Vite dev server). Vite also proxies `/api` and `/health` → `:8000`, so CORS is a fallback.
- **DEMO-BE-9 Settings:** `demo_enabled: bool = False`, `demo_fixtures_dir: Path = tests/fixtures`, `demo_dataset_dir: Path = benchmarks/dataset` (Rev 3), `demo_ground_truth_dir: Path = benchmarks/ground_truth`, `demo_results_dir: Path = benchmarks/results`.
- **DEMO-BE-10 `RecordingJevClient`** (Rev 2, F8): a thin `JevClient` decorator in `jev_client/recording.py` that forwards to the real client and keeps the raw `ChoiceResult` / `ScoreResult` / `NoulResult` of each call. The compare/pipeline endpoints and the benchmark runner wrap the client with it, and return or aggregate `tokens_used`, `level_probabilities` and raw Jev latency **without changing module response models**. The compare response gains `jev_raw: [{primitive, question, result}]`.
- **DEMO-BE-11 Demo config endpoint** (Rev 2, F7): `GET /api/v1/demo/config` returns default thresholds from `Settings` (the three currently-unused fields), the mode and the model id. Sliders initialise from it.

### New Files

```
src/jev_fhir/
├── baselines/                 # moved from benchmarks/baselines (DEMO-BE-1)
├── jev_client/recording.py    # RecordingJevClient (DEMO-BE-10)
├── demo/
│   ├── __init__.py
│   ├── catalog.py             # fixture + ground-truth catalog
│   ├── compare.py             # Jev module + rule baseline + serialized state + jev_raw
│   ├── feed.py                # DecisionFeed ring buffer + SSE fan-out
│   └── pipeline.py            # paced batch runner + lane assignment
└── routes/demo.py
tests/test_demo_api.py
web/
├── package.json · vite.config.ts · tailwind.config.ts · index.html
└── src/
    ├── api/ (client.ts, schema.d.ts generated)
    ├── components/ (ModeBadge, JsonView, FlatStateTable, ScoreGauge,
    │                ProbabilityBars, NoulMeter, ThresholdSlider, VerdictStrip,
    │                ArtifactTabs, LiveFeed, LaneBoard, Sparkline,
    │                ConfidenceHistogram, CalibrationChart, ObservabilityDrawer)
    ├── pages/ (Overview, Studio, Pipeline, Benchmarks, Playground)
    ├── scenes.ts
    └── main.tsx
```

### Makefile Additions

```
make web-install   # npm ci in web/
make web-dev       # vite dev server on :5173 (proxy → :8000)
make web-build     # build to web/dist
make web-types     # regenerate src/api/schema.d.ts from /openapi.json
make demo          # web-build + DEMO_ENABLED=true serve → open http://127.0.0.1:8000/demo
make bench-live    # (Rev 2) MOCK_JEV=false python -m benchmarks.bench_runner --live
make smoke-live    # (Rev 2) one real Jev call per module; prints decision, latency, tokens
make dataset       # (Rev 3) python scripts/generate_dataset.py --seed 42
make bench-full    # (Rev 3) mock benchmark over unit + hard + generated tiers
make bench-live-full  # (Rev 3) live benchmark over the full dataset (manual, costs tokens)
```

---

## 5. Implementation Phases

> **The step-by-step build instructions, exact contracts and per-phase evaluation checklists live in the [Demo Technical Implementation Plan](Jev%20×%20FHIR%20—%20Demo%20Technical%20Implementation%20Plan.md).** This section is the summary. Where the two differ, the implementation plan wins.

Same workflow as the Phases doc: **Codex builds → evaluate in a fresh session → fix → next**. Each phase must pass before the next starts.

```
Phase D0 (live readiness) → D0.5 (benchmark dataset) → D1 (demo API) → D2 (UI shell + Studio) → D3 (Live Pipeline) → D4 (Benchmarks, presenter mode, rehearsal)
```

**Rev 3 change:** D0.5 was added because the current fixtures can't produce meaningful evidence (F10). It comes before D1 because the demo API's fixture catalog and the scene presets are built from this dataset.

**Rev 2 change:** D0 grew from a small cleanup into **live readiness**. The findings in §1.3 have to be fixed before any UI work, because the UI would otherwise present untrustworthy live numbers. D1–D4 are unchanged apart from the Rev 2 items marked below.

### Phase D0: Live Readiness & Cleanup

**Codex instructions:**

**Step 1 — Cleanup (F9):**
- ✅ *Done Sep 24:* README rewritten; the `detect-notifiable` curl was fixed and verified to return 200.
- ✅ *Done Sep 24:* the real key moved from `.env.example` to `.env` (git-ignored, mode 600), and `.env.example` now holds `your-key-here`. Tests still pass (48/48).
- Add `web/node_modules/` and `web/dist/` to `.gitignore`.

**Step 2 — Live client hardening (F4, F5, F6):**
- New settings: `jev_model: str = "jev-latest"`, `jev_timeout_s: float = 5.0`, `jev_max_retries: int = 2`. Pass them to `AsyncTypeSafeClient(model=..., timeout=..., retry=RetryPolicy(max_retries=..., timeout=<overall budget, e.g. 12s>))`.
- Map SDK errors before wrapping. Keep `JevClientError` as the base class and add subclasses or an `error` code:
  - `TypeSafeAPITimeoutError` → 504 `jev_timeout`
  - `TypeSafeRateLimitError` → 429 `jev_rate_limited`
  - `TypeSafeAuthenticationError` / `TypeSafePermissionDeniedError` → 502 `jev_auth`
  - everything else → 502 `jev_error`, with the SDK exception class name in `detail`
- `/health` adds `"jev_model"` (the model id in live mode, `null` in mock mode).

**Step 3 — Noul probability convention (F3):**
- Document on `NoulResult`: `probability` = P(statement is true).
- Fix the `MockJevClient` NIK path: valid → 0.94, invalid → **0.08** (was 0.92).
- Check that `QualityScorer.nik_confidence` and the notifiable thresholds still read correctly under P(true); the notifiable path already uses it.

**Step 4 — `RecordingJevClient` (DEMO-BE-10)** with unit tests.

**Step 5 — Benchmark runner goes live (F2):**
- Add a `--live` flag. It builds `LiveJevClient` from `Settings`, wrapped in `RecordingJevClient`. `mode` becomes `"live_jev"` or `"mock_jev"`, and the report records `jev_model`.
- Sum real `tokens_used` and compute `estimated_cost_usd` at $42 per billion tokens.
- Add a `--limit N` option for cheap partial runs.
- Add `make bench-live`. Plain `make bench` stays mock and offline (CI-safe).

**Step 6 — Quality ground truth rework (F1):** relabel `benchmarks/ground_truth/quality_scores.json` with **bands**, not points, and add an **`expected_action`** (`auto_accept` / `review_needed` at threshold 70). Suggested bands: complete ≥ 70; partial 40–79; sparse 0–45; bands may overlap. Quality accuracy becomes **action agreement** (primary) plus score-in-band (secondary). Labels must be written from a human reading of the fixture, **not** from `field_completeness`. This one needs Budi's sign-off (Open Question 6).

**Step 7 — Baselines and settings:** move baselines into `src/jev_fhir/baselines/` (DEMO-BE-1), add the demo settings (DEMO-BE-9), and make routes/modules read the three threshold settings as defaults (F7).

**Step 8 — Live smoke (`make smoke-live`):** a small script that makes one real call per module on `complete_patient`, `lab_bundle` and `japanese_encephalitis_a83`, and prints decision, probability, latency and tokens. **Budi runs this by hand** with the real key; it is not part of `make test`.

**Step 9 — First live benchmark (baseline):** Budi runs `make bench-live` on the current 50 fixtures and commits the report. Rev 3: this is a **baseline run** that proves the live path end to end. The evidence for Scene 5 and the choice of scene presets now come from the D0.5 dataset run.

**Evaluation checklist:**

```
☐ make lint / typecheck / test all green; coverage stays ≥ 95%
☐ make bench (mock) still runs offline; router/notifiable numbers unchanged; quality now reported as action agreement
✅ README detect-notifiable curl returns 200 against make serve (done Sep 24)
✅ .env.example contains no real credential (done Sep 24)
☐ Old key rotated in the TypeSafe dashboard (manual, Budi)
☐ LiveJevClient passes model / timeout / RetryPolicy from Settings (asserted in test via mocked SDK)
☐ Each mapped SDK error → correct HTTP status + error code (4 tests)
☐ /health includes jev_model
☐ Mock NIK invalid → probability < 0.5; test asserts P(true) semantics for mock + live
☐ RecordingJevClient captures tokens + level_probabilities; bench report tokens_used > 0 in live mode
☐ quality_scores.json has no single-point ranges; every entry has expected_action
☐ benchmarks/ has no baseline logic (imports only)
☐ Threshold settings are read (grep shows usages outside config.py)
☐ make smoke-live succeeds with the real key (manual, Budi) — record latency + tokens in the evaluation note
☐ benchmarks/results/ contains one mode=live_jev report (manual, Budi)
```

### Phase D0.5: Benchmark Dataset (Rev 3)

**Depends on:** D0 complete (live bench runner, banded quality labels, the P(true) convention).

**Goal:** a benchmark dataset that (a) reaches the PRD's evaluation sizes, (b) contains cases where rules and a learned model **should disagree**, and (c) provides realistic demo presets, while the unit-test fixtures stay small and fast.

**Labelling rules (all tiers):**
- Never derive a label from the logic being evaluated: not `field_completeness`, not the rule baselines, not `MockJevClient`. This is the F1 lesson.
- **Hard-case and quality labels are written or approved by Budi.** Codex drafts them with a one-line `rationale` field for each; Budi signs off (Open Question 8).
- Generated bundles may be labelled **by construction**, since the generator decides what clinical content a bundle carries. Genuinely ambiguous mixes are labelled `unknown`.
- Every label records `source` (`unit` / `hard` / `generated` / `demo`), `difficulty` (`easy` / `hard`) and `rationale`.

**Layout:**

```
tests/fixtures/                    # unchanged; unit tests only (50 files)
benchmarks/dataset/
├── hard/          {patients,observations,conditions,bundles}/   # hand-written edge cases
├── generated/     {patients,observations,bundles}/              # seeded generator output (committed)
├── demo/          …                                             # realistic presets for scenes
└── labels/        quality.json · bundle_routes.json · notifiable.json   # one label file per module, all tiers
scripts/generate_dataset.py         # seeded, deterministic; re-running gives byte-identical output
```

**Step 1 — Observation fixtures (new resource type, ~10):** complete lab result (LOINC, `valueQuantity`, subject, encounter, `effectiveDateTime`); vital sign (LOINC 8867-4 heart rate); missing value; missing code system; `status: entered-in-error`; `valueString` in place of quantity; no subject; a unit that doesn't fit the code (e.g. haemoglobin in `mmol/L` vs `g/dL`, legitimate but unusual); future `effectiveDateTime`; a local code only (no LOINC).

**Step 2 — Hard cases (~25), where exact-code rules and field counting should struggle:**

| Module | Case | Expected | Why it's hard for rules |
| --- | --- | --- | --- |
| Notifiable | ICD-10 sub-codes: `A15.0`, `B50.9`, `A01.0`, `A91` with display "Dengue haemorrhagic fever" | notifiable | Exact lookup has `A15`, not `A15.0` |
| Notifiable | Dengue coded **SNOMED only** (38362002), TB SNOMED-only (56717001) | notifiable | No ICD-10 code to look up |
| Notifiable | **Text-only** Condition: `code.text` = "Demam berdarah dengue (DBD)" / "TB paru" | notifiable | No coding at all; Indonesian text |
| Notifiable | Notifiable code but `verificationStatus: refuted` or `entered-in-error` | **not** notifiable (or review) | Rule sees the code and flags it |
| Notifiable | Code/display mismatch: code `J06.9`, display "Dengue fever" | review | Contradictory input |
| Notifiable | Near-miss non-notifiable: `R50.9` fever unspecified, `B34.9` viral infection unspecified, `J18.9` pneumonia | not notifiable (R50.9 may be review) | Looks infectious or dengue-like; tests over-flagging. (A02–A09 avoided until Open Question 9 is settled.) |
| Quality | NIK **formatted**: `3173.0101.0190.0001`, `3173 0101 0190 0001` | present but needs normalisation (review) | Length ≠ 16 but the ID is real |
| Quality | NIK 16 chars with **letters**; NIK all zeros; NIK under a wrong `system` URL | NIK invalid | Length check passes |
| Quality | Placeholder values: name `"-"`, `"unknown"`, `"test"`; address `"."` | review | Field present, so the count says complete |
| Quality | `birthDate` in the future; `birthDate` 1850 | review | Field present and well-formed |
| Router | **Realistic lab submission**: Patient + Encounter + DiagnosticReport + 6 Observations | `lab_result` | Has an Encounter, so the rule says `encounter_summary` |
| Router | Immunization bundle that also carries Patient + Encounter + Practitioner | `immunization_report` | Encounter-first rule order |
| Router | `transaction` bundle (with `request` entries) for a medication dispense | `medication_dispense` | Different bundle type, same content |
| Router | Vital-sign-only Observations (no lab LOINC class) | `encounter_summary` or `unknown` (Budi decides) | Observation ≠ lab |
| Router | Genuinely mixed: 3 labs + 2 immunizations + 1 dispense | `unknown` | No dominant category |

**Step 3 — Generator (`scripts/generate_dataset.py`) to reach PRD sizes:**
- Seeded (`--seed 42`) and deterministic; output is committed, so benchmarks don't depend on re-running it.
- **Bundles → 100 total** (including the unit and hard sets): ~20 per real category plus ~20 `unknown`. Vary entry count (1–30), resource order, `collection` vs `transaction` vs `batch` type, whether Patient/Encounter/Practitioner are present, and a realistic LOINC pool (CBC, glucose, HbA1c, creatinine, dengue NS1 / IgM).
- **Quality → 50+ total** across Patient and Observation: synthetic Indonesian names and addresses (province/city codes), valid and invalid NIKs, controlled defects (one or two per resource). The generator emits a *draft* label with the defects it injected; Budi approves the final band and action.
- No real names or NIKs: NIK region/date parts are random but well-formed; names come from a small built-in list.
- **Synthea** (mentioned in the PRD) is optional later. It is heavier to run, isn't Indonesia-specific, and would need a post-processing step for NIKs, so it's not worth it for this PoC.

**Step 4 — Demo presets (~6, in `benchmarks/dataset/demo/`):** hand-polished, realistic-looking resources for each scene. A complete Indonesian patient; the same patient with a dotted NIK; a 9-entry lab submission; a JE Condition from a Bali clinic; a text-only DBD Condition; one genuinely ambiguous bundle. Final picks are made after the live run (Step 6).

**Step 5 — Benchmark runner:** add `--dataset {unit,full}` (default `unit`, so `make bench` stays fast and unchanged). `full` loads every tier from `benchmarks/dataset/labels/`. The report breaks accuracy down **by `source` and `difficulty`**, so "easy" and "hard" results are never averaged together. Add `make bench-full` (mock) and `make bench-live-full`.

**Step 6 — Live run on the full dataset (manual, Budi):** `make bench-live-full`. This report replaces the D0 baseline as the evidence for Scene 5 and decides the final demo presets. Record the cost from real `tokens_used`; roughly 200 calls is still well under the PRD's $0.01 budget.

**Evaluation checklist:**

```
☐ make lint / typecheck / test all green; unit-test fixture count unchanged (50) and test time roughly unchanged
☐ tests/fixtures/observations/ has ≥ 10 valid FHIR R4 Observations; quality scorer tests cover them
☐ benchmarks/dataset/hard/ has ≥ 25 cases covering every row of the Step 2 table
☐ Totals incl. unit set: ≥ 100 bundles, ≥ 50 quality resources (Patient + Observation), ≥ 30 conditions
☐ Every routing category has ≥ 15 labelled bundles; unknown ≥ 15
☐ All dataset files parse as valid FHIR R4 (fhir.resources) — one parametrised test over the dataset
☐ Every label has source, difficulty, rationale; hard + quality labels marked approved_by: budi
☐ No label is computed from field_completeness, rule baselines, or MockJevClient (reviewer greps generator + label files)
☐ generate_dataset.py --seed 42 twice → identical output (test)
☐ No real-looking PII: names from built-in list, NIKs synthetic (spot-check 10)
☐ make bench-full (mock) report shows per-source and per-difficulty accuracy; rules visibly fail on the hard sub-code / SNOMED / text-only rows
☐ benchmarks/results/ contains a mode=live_jev, dataset=full report (manual, Budi)
```

### Phase D1: Demo API

**Codex instructions:** Implement DEMO-API-1 … DEMO-API-6 (DEMO-API-7 read-only; `run` optional), DEMO-BE-2 … DEMO-BE-8, and (Rev 2) DEMO-BE-10/11 wiring. Tests in `tests/test_demo_api.py` use the mock client only; the expected values below are mock values.

**Evaluation checklist:**

```
☐ make lint / typecheck (strict) / test all green; coverage ≥ 95% overall
☐ Demo routes return 404 when DEMO_ENABLED=false
☐ /demo/fixtures returns 50 entries, each with ground_truth (quality entries carry expected_action)
☐ Fixture path traversal (../../.env) rejected with 400/404
☐ /demo/config returns thresholds from Settings + mode + jev_model
☐ compare/quality on complete_patient (mock) → jev.action=auto_accept, rule present, serialized_state has field_completeness, jev_raw has score + noul entries with tokens_used
☐ compare/router on mixed_bundle with confidence_minimum=0.99 → category unknown, override_applied=true
☐ compare/notifiable on japanese_encephalitis_a83 → Flag + valid AuditEvent (parse via fhir.resources)
☐ Pipeline run over 50 fixtures emits 50 SSE decision events, each with lane + lane_reason
☐ Decision feed ring buffer caps at 500
☐ Existing Phase 4 tests pass unchanged; Phase 4 response schemas unchanged in /openapi.json
```

### Phase D2: UI Shell, Overview, Studio

**Codex instructions:** Scaffold `web/` (§3.1), generate API types, and build global elements (UI-G-1 … G-6), Overview (UI-O-*), Studio (UI-S-*) and Playground (UI-PL-*). Wire `make web-*` and `make demo`.

**Evaluation checklist:**

```
☐ make demo serves the UI at /demo; refresh on /demo/studio works (SPA fallback)
☐ npm run lint + tsc --noEmit clean
☐ Mode badge reflects /health; mock tooltip text present
☐ Studio: all three tabs render input / what-Jev-sees / decision for every fixture without error
☐ Quality threshold 70→85 on complete_patient flips auto_accept → review_needed
☐ Router floor slider can force mixed_bundle to unknown with override note
☐ Notifiable JE shows Flag tab + Dinkes card; common cold shows neither
☐ Verdict strip matches ground truth for all 50 fixtures (spot-check 10)
☐ Playground: malformed Condition shows 422 card with request_id
☐ Screenshots at 1280×720 and 1920×1080 attached to the evaluation
```

### Phase D3: Live Pipeline & Observability Drawer

**Codex instructions:** Build the Live Pipeline screen (UI-P-*) on DEMO-API-5/6 and the observability drawer (UI-G-4).

**Rev 2, live-mode constraints:** one full run is ~70 real Jev calls (Patients make two calls each: score and NIK). In live mode:
- The server caps concurrency at 4 in-flight calls and pace at 10/s.
- A `jev_rate_limited` or `jev_timeout` error puts that item in the Review lane with the reason `jev error: <code>`, and the run continues.
- The stats strip shows running tokens and cost.

**Evaluation checklist:**

```
☐ Start → 50 items stream at chosen pace; lanes + counters sum to 50
☐ (Rev 2) Injected Jev error on one item (mock test double) → that item lands in Review with jev error reason; run completes
☐ Pause/stop/reset behave; closing tab doesn't leave a server run going forever (run stops or finishes)
☐ Re-run with higher thresholds shows positive Δ review-queue
☐ Review items show correct lane_reason
☐ Sparkline + histogram update live; no console errors
☐ Drawer shows last request id/duration and parsed metrics
```

### Phase D4: Benchmarks, Presenter Mode, Rehearsal

**Codex instructions:** Build the Benchmarks screen (UI-B-*), scene presets and keyboard controls (UI-D-*), and polish per UI-NFR-*.

**Evaluation checklist:**

```
☐ Benchmarks shows latest report, PRD target chips; failing targets shown as FAIL (mock router: 0.733)
☐ Mock disclaimer visible for mock_jev reports; live reports show model id, tokens, cost
☐ Live vs mock side-by-side renders when both reports exist
☐ "Where Jev lost" rows come from the selected report; each opens Studio with that fixture
☐ Scene presets chosen from the D0.5 full-dataset live report (fixtures that show each point clearly), not from mock values
☐ Benchmarks screen shows accuracy split by source (unit / hard / generated) and difficulty; never one blended number
☐ Scenes 0–6 load via → with no manual input; R resets scene
☐ Full dry run of §2 in ≤ 13 minutes in LIVE mode from a cold `make demo`
☐ Full dry run in MOCK mode (fallback) — every scene still makes sense with mock values
☐ No browser requests leave localhost (the server's Jev calls are the only outbound traffic)
```

---

## 6. Demo Day Checklist

```
☐ make lint typecheck test bench — all green on demo machine
☐ make demo from cold start; open /demo; mode badge correct
☐ Live mode: make smoke-live passes on venue network; /health shows "live" + jev_model; fallback plan = restart with MOCK_JEV=true (< 30 s)
☐ Latest bench report matches the mode being presented
☐ Browser at 125% font scale; notifications off; presenter notes on second screen
☐ Rehearsed Q&A: "why not just rules?", "how is confidence calibrated?", "what data does Jev see?", "PHI?" (none — synthetic, flat state only)
```

---

## 7. Open Questions

1. **Live Jev access (Rev 2: partly answered):** the SDK client is built and unit-tested, but no real call has been made yet. D0 Step 8 (`make smoke-live`) answers this. If live fails, the pitch falls back to "the architecture and harness are ready; here's the mock", with no accuracy claims.
2. **Mock routing behaviour:** leave the mock as-is, or make it return confidence < 0.5 on bundles with no signal so UC-2's `unknown` path shows up naturally? **Recommendation (unchanged):** leave it. With live as the primary mode, the mock's weakness only appears in the fallback, where the disclaimer covers it.
3. **Scene 6 LLM layer:** keep it as a dimmed "next" diagram (recommended), or build a minimal "escalate to Claude" button for review-queue items? The latter adds an LLM dependency and roughly one phase of work.
4. **Credential in `.env.example` (resolved Sep 24, 2026):** confirmed real. Moved to an untracked `.env` (mode 600); `.env.example` now holds `your-key-here`. **Remaining (Budi):** rotate the key in the TypeSafe dashboard and put the new one in `.env`.
5. **Recording:** also produce a 3-minute screen recording of Scenes 1, 3 and 4 as a backup and for the dev.to write-up? Rev 2: record it in **live** mode after D4, so there is a live fallback even if the API is down on demo day.
6. **(Rev 2) Quality ground truth:** approve relabelling `quality_scores.json` as bands + `expected_action` (D0 Step 6)? The labels are the benchmark's source of truth, so a human should write or approve them, not the agent that builds the scorer. Without this, no live quality accuracy number can be shown.
7. **(Rev 2) Model pinning:** `jev-latest` can change between rehearsal and demo. If TypeSafe publishes versioned model ids, pin one in `JEV_MODEL` for the demo week.
8. **(Rev 3) Label ownership for D0.5:** Codex drafts hard-case and quality labels with a rationale; you approve them (`approved_by: budi`). Roughly 75 labels to review. It's about an hour, and it's what makes the benchmark credible. Agreed?
9. **(Rev 3) Notifiable scope conflict:** PRD FR-4.2 lists **A00–A09** (cholera, typhoid *and* other intestinal infections), but `data/notifiable_diseases.json` only has A00 and A01. Which is right for Indonesian reporting? Until this is settled, D0.5 avoids A02–A09 in hard cases so the labels don't depend on it.
10. **(Rev 3) Router edge labels:** should a bundle with only vital-sign Observations be `encounter_summary` or `unknown`? One call from you, applied consistently.
