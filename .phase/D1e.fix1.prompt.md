D1e fix-up round 1. Same rules as before (AGENTS.md and the D1e prompt). TESTS ONLY: don't change any file
under src/, the Makefile or the snapshot.

The evaluator reproduced D1e: gates green, the code matches the contract, and all 14 Final D1 checklist items
pass on a real server. But a mutation check found two tests that pass even when the behaviour they're named for
is removed, so they don't prove the security properties:

1. `test_static_ui_serves_assets_and_never_serves_traversal_paths` (tests/test_demo_api.py)
   - Mutation: in src/jev_fhir/demo/static.py, change
     `if candidate.is_relative_to(dist_root) and candidate.is_file():` to `if candidate.is_file():`.
     The test still PASSES.
   - Why: the traversal requests resolve relative to the temporary dist folder
     (`tmp_path/dist/../../pyproject.toml`), where no such file exists, so the SPA fallback is returned
     either way.
   - Fix: create a real file OUTSIDE the dist folder but reachable by traversal, e.g.
     `(tmp_path / "secret.txt").write_text("TOP-SECRET")`, and request
     `/demo/%2e%2e/secret.txt` and `/demo/..%2fsecret.txt`. Assert both reach the static handler, return
     index.html content, and never contain "TOP-SECRET". Also add a symlink inside dist that points to that
     outside file (e.g. `dist/leak.txt -> ../secret.txt`) and assert `/demo/leak.txt` returns index.html, not
     "TOP-SECRET".
   - Done means: with the mutation above applied, this test FAILS; with the real code, it passes.

2. `test_benchmark_missing_directory_and_bad_names_never_read_files` (tests/test_demo_api.py)
   - Mutation: in src/jev_fhir/demo/benchmarks.py, change `if REPORT_NAME_RE.fullmatch(name) is None:` to
     `if False:`. The test still PASSES.
   - Why: it points at a MISSING results directory, so every name returns 404 regardless.
   - Fix: add a test (or extend this one) with a REAL temporary results directory containing a valid report
     (`bench_20260924T083443Z.json`) AND a non-report JSON file, e.g. `notes.json` with `{"secret": true}`.
     Assert `/api/v1/demo/benchmarks/notes` → 404 ErrorResponse `not_found`, with no "secret" in the body,
     while the valid name returns the report. Also prove "no filesystem access" for invalid names: patch
     `pathlib.Path.read_text` (as tests/test_demo_catalog.py does) to raise if called, and request the invalid
     names.
   - Done means: with the mutation above applied, this test FAILS; with the real code, it passes.

Run each mutation yourself to confirm the new tests fail under it, then restore the source files exactly (check
with `git diff --stat src/`, which must show only the D1e changes that existed before this fix-up).

Verify: `make lint && make typecheck && make test` green. Report back with the changed test names, test count
before (407) → after, and, for each of the two mutations, the pytest line showing the new test FAILING under it.
