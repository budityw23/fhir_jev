D1e fix-up round 2 (the last allowed). TESTS ONLY: don't change src/, the Makefile or the snapshot. Same rules
as before.

Round 1 worked: both mutation-strengthened tests now fail under their mutations (the evaluator reproduced that).
But while rewriting `test_benchmark_missing_directory_and_bad_names_never_read_files`, three assertions from
the previous version were DROPPED. That's a weakening, which isn't allowed, even as a side effect:

1. A missing results directory → `GET /api/v1/demo/benchmarks` returns `[]`. The test is still named
   "missing_directory" but no longer checks it. benchmarks.py line 31 is now uncovered.
2. A well-formed but nonexistent report name, `bench_20990101T000000Z` → 404 ErrorResponse `not_found`.
   benchmarks.py lines 63–64 (the FileNotFoundError → DemoNotFoundError path) are now uncovered.
3. The encoded traversal name `%2e%2e%2fbench_20260924T083443Z` → 404.

Fix: restore all three. Keep everything round 1 added (the real results dir, notes.json, the read_text patch,
the secret checks). You may split them into a separate test, e.g.
`test_benchmark_missing_directory_and_missing_reports_return_empty_or_404`, so each test's name matches what it
asserts.

Done means:
- src/jev_fhir/demo/benchmarks.py back to 100% coverage
- `make lint && make typecheck && make test` green
- no other assertion removed anywhere (compare against your round-1 version of the file)

Report back with the test names, test count before (407) → after, and the benchmarks.py coverage line.
