---
description: Orchestrate a plan phase end to end (Codex implements headless, Claude evaluates, commits on PASS)
argument-hint: <phase> [--through <phase>] [--auto]
---

# /phase-loop $ARGUMENTS

You orchestrate one or more phases of `docs/Jev × FHIR — Demo Technical Implementation Plan.md`.
**Codex implements** (headless, in the background); **you evaluate** with the same rigor as the
D1a–D1c evaluations recorded in the plan; you commit on PASS. Budi supervises from his phone
through Remote Control, so every stop and summary must be short and readable on a phone.

## Arguments

- `<phase>`: the first phase to run, e.g. `D1d`.
- `--through <phase>`: the last phase allowed (inclusive). Default: `<phase>` only.
- `--auto`: after a PASS, continue straight into the next phase (up to `--through`). Without
  `--auto`, **stop after every phase** and wait for Budi, even when `--through` is given.

Phase order: `D1d → D1e → D2 → D3 → D4` (read the plan headings if later phases are added).

## Fixed facts about this machine (verified Sep 27, 2026)

- Codex CLI lives under nvm and is NOT on the non-interactive PATH. Always use:
  ```bash
  export PATH="$HOME/.nvm/versions/node/v24.13.0/bin:$PATH"   # provides node + codex
  CODEX="$HOME/.nvm/versions/node/v24.13.0/bin/codex"
  ```
- `codex exec` flags used: `--json` (JSONL events on stdout), `-o <file>` (final message),
  `--full-auto` (workspace-write sandbox, no approvals), `-C <dir>`, prompt from stdin via `-`,
  `-c key=value` config overrides.
- `codex exec resume <SESSION_ID> [PROMPT]` has **no `-C` and no `-s`**. It filters sessions by
  cwd, so run it **from the repo root**. It accepts `--json`, `--full-auto`, `-o`, `-c`.
- The session ID is `thread_id` in the **first** `{"type":"thread.started",...}` event of the
  `--json` stream.
- The workspace-write sandbox disables network by default; phases need uvicorn + curl on
  localhost, so pass `-c sandbox_workspace_write.network_access=true`.
- `~/.codex/config.toml` selects model `gpt-5.6-terra`; **CLI 0.125.0 is too old for it** (the
  server answers "requires a newer version of Codex"). Budi upgrades with
  `npm install -g @openai/codex@latest` under Node v24.13.0. The preflight enforces this.
- The `rtk` hook rewrites `curl` and `git diff` output. Use `rtk proxy curl ...` and
  `rtk proxy git ...` whenever you parse output.
- Never `pkill -f <pattern>` when the pattern appears in your own command line (it kills your
  shell). Start servers with `&`, keep `PID=$!`, and `kill $PID; wait $PID`.

## Step 0 — Preflight (once per invocation; any failure → STOP)

1. **Git:** `git status --porcelain` is empty; the branch is `main`; record `HEAD` as the
   phase's base commit.
2. **Codex:** `$CODEX --version`; `$CODEX exec --help` still lists `--json`, `-o`, `--full-auto`;
   `$CODEX exec resume --help` exists. If the flags changed, adapt this procedure only if the
   meaning is unambiguous; otherwise STOP.
3. **Codex smoke test** in a scratch dir (NOT the repo), about 30 s:
   ```bash
   T=$(mktemp -d) && cd "$T" && git init -q .
   echo 'Run exactly: python3 -m http.server 18799 >/dev/null 2>&1 & sleep 1; curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18799/; kill %1. Reply with only the status code.' \
     | timeout 300 "$CODEX" exec --json --full-auto -c 'sandbox_workspace_write.network_access=true' -o "$T/last.md" - > "$T/events.jsonl" 2> "$T/stderr.txt"
   ```
   Expect exit 0 and `200` in `last.md`.
   - `requires a newer version of Codex` → STOP: *"Upgrade Codex CLI: `npm install -g @openai/codex@latest` (Node 24.13)."*
   - Localhost blocked → STOP and ask whether to allow `--dangerously-bypass-approvals-and-sandbox`.
     Never use that flag without Budi's explicit yes.
   Delete `$T` afterwards.
4. **Baseline:** `make lint && make typecheck && make test` must be green on the base commit.
   Record the test count and coverage; they are the phase's "before" numbers.

## Per phase

### 1. Prepare

- If `.phase/<P>.prompt.md` exists, use it **as-is**. Sanity-check it against the plan's phase
  section (scope, contract refs, Verify) and `.phase/progress.md`. If they conflict, STOP.
- Otherwise write `.phase/<P>.prompt.md` from the plan section, `AGENTS.md` and `progress.md`, in
  the house structure used by `.phase/D1d.prompt.md`:
  - **Header:** which phase; "Follow AGENTS.md; read .phase/progress.md first"; which plan
    sections to read; "the contract is the source of truth: stop and explain, don't redesign".
  - **Scope:** exact files and behaviour, spelling out everything the contract leaves implicit
    (field mappings, error cases, ordering, edge cases), as in the D1b–D1d prompts.
  - **Tests:** contract tests quoted verbatim, plus the extra tests that make them meaningful.
  - **Out of scope:** the deferred list from the plan.
  - **Phase-specific rules** (only what AGENTS.md doesn't already say).
  - **Verify:** make targets, plus curls against a real uvicorn process; ask for real output.
  - **Report back with:** "everything AGENTS.md's Final message asks for (test count before: N)"
    plus phase-specific evidence.
  - Frontend phases (D2+): include the nvm PATH line and the `web/` commands.

### 2. Implement (background)

Run Codex **in the background** (Bash `run_in_background: true`) and wait for the completion
notification. Never poll in a tight loop.

```bash
cd /home/budi/code/sphere_project/FHIR_JEV
export PATH="$HOME/.nvm/versions/node/v24.13.0/bin:$PATH"
P=<phase>
timeout 4h "$CODEX" exec --json --full-auto \
  -c 'sandbox_workspace_write.network_access=true' \
  -C "$PWD" -o ".phase/$P.result.md" - < ".phase/$P.prompt.md" \
  > ".phase/$P.log" 2>&1
echo $? > ".phase/$P.exit"
```

When notified, extract and save the session ID:

```bash
python3 -c "import json,sys
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except Exception: continue
    if e.get('type')=='thread.started': print(e['thread_id']); break" ".phase/$P.log" > ".phase/$P.session"
```

### 3. Check the handoff (any failure → STOP, except where noted)

- `.phase/$P.exit` is `0` (124 = timed out) and `.phase/$P.result.md` exists and isn't empty. If
  not, read the tail of `.phase/$P.log` for the reason.
- Read the result file fully. If Codex **ends with a question**, or reports something it
  **couldn't implement**, or asks for a decision, STOP and relay it.
- `git rev-parse HEAD` still equals the base commit (Codex must not commit).
- `rtk proxy git status --porcelain` and `rtk proxy git diff --stat`: every changed or new path
  must be within the phase scope. That means the prompt's Scope files, the phase's test files,
  and `.phase/$P.*`. Anything else is out of scope: the plan doc, `AGENTS.md`, `.phase/progress.md`,
  `.gitignore`, `pyproject.toml`, `.env*`, fixtures, labels, `tests/test_api.py`, or earlier
  phases' modules beyond what the prompt allows. Any of those → STOP.

### 4. Evaluate (don't trust the report; reproduce everything)

Hold the same bar as the D1a–D1c evaluations in the plan:

1. **Gates:** `make lint && make typecheck && make test`; record the test count (before → after),
   per-file coverage for touched files (≥ 90% each, TOTAL ≥ 95%), and the suite runtime.
2. **Contract read-through:** read every new or changed source file against the contract and the
   phase section (names, fields, signatures, exact strings, status codes, error bodies).
   Deviations are ❌.
3. **Real server:** start `DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 187xx &`,
   keep `PID=$!`, and run **every** checklist curl yourself with `rtk proxy curl`. Compare with
   Codex's pasted output. Check the server log for tracebacks. Then `kill $PID; wait $PID`.
4. **Tests that prove something:** for each key behaviour, plant a bug (copy the file first,
   record `sha1sum`), run the matching test, confirm it FAILS, then restore and verify the checksum
   is byte-identical. Probe failure paths the tests may miss (as the D1c unexpected-exception
   probe did).
5. **No weakening:** `rtk proxy git diff` on pre-existing test files. Removed or relaxed
   assertions, loosened validators, lowered thresholds or new `type: ignore`s without a reason
   are ❌. `tests/test_api.py` must be unchanged.
6. **Hygiene:** no throwaway files left (e.g. new `benchmarks/results/bench_*` from verification);
   `.env` untracked; no secrets (`grep -q "apikey_[0-9a-f]\{12,\}"` over every changed file).
7. **Scope:** nothing from later phases implemented early.

Classify every finding as ✅ / ⚠️ (non-blocking) / ❌ (blocking), with evidence, as in the plan's
D1c record.

### 5. Decide

- **PASS** (no ❌):
  1. In the plan's phase section, replace each checklist `☐` with `✅` or `⚠️` plus evidence, add
     an "Issues found" block if any, and fill in the Evaluation Record. **Never change the wording
     of Verify or checklist items**; only add results.
  2. Append the phase entry to `.phase/progress.md` in the existing format: what was built,
     choices beyond the contract, known gaps, verdict, tests before → after.
  3. Commit, one commit per phase: `git add -A` (after re-checking scope and secrets); message
     `feat: <what> (phase <P>)` with a body explaining why. Include `.phase/$P.prompt.md`,
     `.result.md`, `.session` and any fix files; `.log` and `.exit` are git-ignored or deleted.
     **No `Co-Authored-By` or other trailer** (Budi's global rule). **Never push**, and never use
     `--force`, `--amend` or a rebase.
  4. Stop, or with `--auto`, continue with the next phase if it's within `--through`.
- **FIXABLE** (❌ items Codex can fix within scope, and no decision needed from Budi):
  1. Write `.phase/$P.fix<N>.prompt.md`: the exact gaps (file:line, expected vs actual, the
     contract quote), what "done" means, and "don't touch anything else; same rules as before".
  2. Resume the **same** session in the background, from the repo root:
     ```bash
     timeout 2h "$CODEX" exec resume "$(cat .phase/$P.session)" --json --full-auto \
       -c 'sandbox_workspace_write.network_access=true' \
       -o ".phase/$P.fix<N>.result.md" - < ".phase/$P.fix<N>.prompt.md" >> ".phase/$P.log" 2>&1
     echo $? > ".phase/$P.exit"
     ```
  3. Repeat steps 3–5 in full. **At most 2 fix-up rounds per phase**; if the third evaluation still
     has ❌, STOP.
- **STOP** when:
  - 2 fix-ups have failed
  - a contract or plan ambiguity needs Budi's decision
  - Codex changed files outside scope or committed
  - the preflight failed
  - anything is destructive or irreversible
  Leave the working tree as it is: don't commit, and don't revert Codex's work. Send the phone
  summary with the decision needed.

You never edit production or test code yourself in this loop. Fixes go back to Codex. You only
edit the plan's checklist and records, `.phase/progress.md`, and `.phase/*` prompt files.

## Phone summary (always end with this; keep it under ~12 lines)

```
<P> — PASS | FIXABLE→PASS (n rounds) | STOP
Tests: <before> → <after>, coverage <total>% (<file> <x>%, …)
Checks: <k>/<n> ✅, <m> ⚠️, <j> ❌
Key: <one line on the most important finding or fix>
Commit: <hash> (not pushed)       ← on PASS
Need from you: <the decision, or "nothing, next: <phase>">
```

## Guardrails (never break these)

- Never push, force, amend, rebase, or rewrite history.
- Never skip evaluation, and never mark a checklist item ✅ without reproducing it yourself.
- Never edit Verify or checklist wording, thresholds or contracts to make a phase pass. A plan
  clarification needs Budi's approval (STOP and propose it).
- Never use `--dangerously-bypass-approvals-and-sandbox` without Budi's explicit yes.
- Mock Jev only; no live API calls during evaluation.
