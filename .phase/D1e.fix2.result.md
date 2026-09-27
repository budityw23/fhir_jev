Restored the dropped benchmark assertions in [tests/test_demo_api.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_demo_api.py).

Tests:
- `test_benchmark_missing_directory_and_bad_names_never_read_files`
- `test_benchmark_missing_directory_and_report_return_empty_or_404`
- Round-1 static traversal/symlink test remains unchanged.

Verification passed:

```text
make lint && make typecheck && make test
408 passed in 8.94s
```

Test count: 407 → 408.

Coverage:

```text
src/jev_fhir/demo/benchmarks.py  41  0  100%
```

No source, Makefile, or snapshot files were changed.