Implement the fix in `docs/Jev × FHIR — Code Text Fix Plan.md`: steps 2 and 3 of its Rollout, meaning
changes 1–4 and the tests. Follow AGENTS.md (standing rules). Read `.phase/progress.md` first. The plan
is the source of truth: if something can't work as written, stop and explain, don't redesign.

**Finish the whole task before you stop.** Earlier sessions stopped early and skipped planted bugs. Don't
end your turn until everything below exists and Verify passes. If you truly can't, list what's missing.

## Decisions already made

- `code_text` is the string in `code.text`, truncated to exactly 200 characters, or `None`.
- A confirmed text-only Condition still creates a Flag: `condition_code` stays `unknown`, and the display
  uses the text.

## Scope (these files only)

- `src/jev_fhir/serializer/condition.py`: add `code_text`. Reuse the existing style; name the limit as a
  module constant.
- `src/jev_fhir/modules/notifiable_detector.py`, the two `condition_display=` lines: use
  `serialized["code_display"] or serialized["code_text"] or "Unknown condition"`.
- `tests/test_serializer.py`: add `"code_text": None` to the exact-match dict at the Condition test, and
  add the new serializer tests.
- `tests/test_decision_modules.py`: add the detector tests.
- `web/src/test/fixtures/compare_notifiable.json`, plus only those generated files `make web-types`
  really changes because of this field. Report each one. If it changes anything else, such as
  `web/src/api/`, explain why.

## Must not change

- `src/jev_fhir/baselines/notifiable.py`, `src/jev_fhir/jev_client/mock.py`, all labels and fixtures,
  `tests/test_api.py`, `tests/snapshots/`, the Phase 4 response models, `pyproject.toml`, `.env*`.
- The owner's uncommitted edits in these seven files must stay byte-identical. Don't edit, stash, restore
  or format them: `web/src/components/benchmarks/BenchmarkParts.tsx`, `web/src/index.css`,
  `web/src/pages/{Benchmarks,Overview,Pipeline,Playground,Studio}.tsx`.
- `docs/`, `web/video/`, `benchmarks/results/bench_20261031T150439Z.*`. Don't re-record the video.
- Don't use `git checkout`, `git restore`, `git stash`, `git reset` or `git clean`. Don't commit.

## Hard rules

- Mock Jev only. Never run `make bench-live*` or `make smoke-live`, and never read `.env`.
- Don't teach the mock to read text, and don't touch labels, thresholds or prompts to improve a result.
- Any `benchmarks/results/bench_*` file you create during verification must be deleted, by exact name.
  Never delete one that existed before you started.

## Tests (the plan's eight, made specific)

1. Text-only Condition: `code_text` set; `code_system`, `code_value` and `code_display` are `None`.
2. Coding plus text: both are kept.
3. No `code`: `code_text` is `None`.
4. 250-character text gives exactly 200 characters; exactly 200 stays unchanged.
5. Non-string `code.text`: assert what really happens (`Condition.parse_obj` should reject it) and say
   which behaviour you found.
6. Stubbed Jev client: the state passed to `noul` contains the text from `dbd_text_only.json`.
7. Stubbed Jev confirming a text-only Condition: the Flag's displayed text contains the `code.text`, not
   "Unknown condition", and the code is `unknown`. The AuditEvent path at the second `condition_display`
   line must also be covered.
8. With the real `MockJevClient`, a text-only Condition is still not notifiable, and adding `code.text`
   to a coded Condition doesn't change `answer` or `probability`.

## Verify (real output)

1. `make lint && make typecheck && make test`. Baseline before you start: 412 tests, TOTAL 98%. Required:
   TOTAL ≥ 95%, each touched module ≥ 90%.
2. In `web/`, with `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`:
   `npm run lint`, `npm run typecheck`, `npm run test`, `npm run e2e`.
   Playwright may rewrite tracked images in `web/e2e/screenshots/`. Report any it changes; don't revert them.
3. Real server on port 18770, then stop it:
   `DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18770`
   Paste the real curl output from the demo compare endpoint for
   `benchmarks/dataset/hard/conditions/dbd_text_only.json`, showing `serialized_state.code_text`. Check
   `src/jev_fhir/routes/demo.py` for the exact request shape.
4. **Planted bugs, run them yourself.** For each: copy the file aside, plant it, run the matching test,
   paste the FAILED summary line, restore it, and show matching `sha1sum` values.
   a. Serializer always returns `code_text: None`.
   b. Remove the 200-character truncation.
   c. Remove `or serialized["code_text"]` from each `condition_display` line, one at a time.
5. `git status --porcelain`, and confirm no stray server is left running.

## Report back

Everything AGENTS.md's Final message asks for (test count before: 412), the planted-bug output, every
generated file that changed, and any assertion in an existing test you had to alter, and why.
