# AGENTS.md — Jev × FHIR

Standing rules for coding agents (Codex) working in this repo. Phase prompts in `.phase/`
add phase-specific scope on top of these rules; they do not repeat them.

## Project

A FastAPI decision layer that sends flattened FHIR **R4** resources to TypeSafe's Jev model
(mock or live) for three decisions: quality score + NIK gate, bundle routing, and
notifiable-disease detection. A demo API (`/api/v1/demo/*`) and, later, a web UI (`web/`)
show it working. Python 3.11+, FastAPI, Pydantic v2, `fhir.resources` (R4B models), structlog,
pytest, ruff, mypy `--strict`.

## Read before you start a phase

1. The phase prompt you were given (usually `.phase/<phase>.prompt.md`).
2. `docs/Jev × FHIR — Demo Technical Implementation Plan.md`: the phase section, and for D1
   the **"D1 Contract (Source of Truth)"**. The contract wins over any summary.
3. `.phase/progress.md`: what earlier phases built, the deliberate choices beyond the contract,
   and known gaps. Build on those; don't undo them.

If the contract or plan can't work as written, **stop and explain in your final message**.
Don't redesign it.

## Code rules

- **Pydantic v2** models. **mypy `--strict`** must pass. A docstring on every module, class and
  public function you add.
- Dependency injection via FastAPI `Depends(...)` through `AppServices` / `DemoServices`
  (`src/jev_fhir/dependencies.py`). No module-level mutable state.
- FHIR models come from `fhir.resources.R4B.*`; fixtures must be valid FHIR **R4**.
- **No new runtime dependencies** in `pyproject.toml` unless the phase prompt explicitly allows it.
- Match the surrounding style: structlog for logging, `_error_response` / `ErrorResponse` for API
  errors, and the Makefile's `$(PYTHON)` (`.venv/bin/python`) convention.
- Don't change what earlier phases defined (contracts, response models, Phase 4 endpoints,
  fixtures, labels, `approved_by`, `.gitignore`) unless the phase prompt says so.

## Tests

- **Mock Jev only.** Never call the live Jev/TypeSafe API from tests or verification.
- **Never weaken** a validator, a test, a threshold or a coverage target to make something pass.
  Fix the code or data, or report why the spec looks wrong.
- Tests must never hang: every stream, poll or background task in a test ends by a limit, a
  disconnect or a timeout.
- Prefer asserting behaviour over current mock numbers; when a mock value is asserted, say so in
  the test name or a comment.
- `tests/test_api.py` (Phase 4) must keep passing unchanged.

## Quality bar (every phase)

```bash
make lint        # ruff check + ruff format --check
make typecheck   # mypy --strict
make test        # pytest with coverage: TOTAL ≥ 95%, each new/changed module ≥ 90%
```

Frontend phases (D2+) add `npm run lint`, `npm run typecheck`, `npm run test` and `npm run e2e`
in `web/`. Node lives under nvm; non-interactive shells need
`export PATH="$HOME/.nvm/versions/node/v24.13.0/bin:$PATH"`, or `source ~/.nvm/nvm.sh && nvm use`.

## Verification against a real server

Whenever the phase touches HTTP behaviour, run the phase's curl checks against a **real uvicorn
process** and paste the **actual output** in your final message. TestClient output doesn't count
as curl output.

```bash
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000
```

Stop the server afterwards. If you can't run it (e.g. sandbox restrictions), say so explicitly
instead of substituting TestClient.

## What you must NOT do

- **Don't commit, push, rebase, or otherwise touch git history.** The evaluator commits.
- **Don't tick checklists or fill in Evaluation Records** in the plan doc, and don't edit the
  plan's Verify or checklist wording. A separate evaluator does that.
- Don't edit `.phase/progress.md`; the evaluator maintains it.
- Don't touch `.env` or print secrets. Use `.env.example` for new settings.
- Delete any throwaway files your verification creates (e.g. benchmark reports under
  `benchmarks/results/`, temp logs, scratch scripts).
- Don't work outside the phase scope. If something outside it seems necessary, describe it in
  your final message instead of doing it.

## Final message (report back)

End with a report containing, at minimum:
- the changed and added files
- test count before → after, and the suite runtime
- per-file coverage for every new or changed source file
- the real curl output requested by the phase
- any additive helper beyond the contract, and anything you couldn't implement exactly as
  written, and why
- any open question for the evaluator, stated plainly at the end
