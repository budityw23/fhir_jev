Strengthened only [tests/test_demo_api.py](/home/budi/code/sphere_project/FHIR_JEV/tests/test_demo_api.py).

Updated tests:
- `test_static_ui_serves_assets_and_never_serves_traversal_paths`
  - Uses an outside `secret.txt` and an escaping symlink.
- `test_benchmark_missing_directory_and_bad_names_never_read_files`
  - Uses a real results directory and patches `Path.read_text` to prove invalid names cause no read.

Mutation proof:

```text
pytest ...::test_static_ui_serves_assets_and_never_serves_traversal_paths -q
FAILED ... AssertionError: 'TOP-SECRET' == '<!doctype html><title>demo app</title>'
```

```text
pytest ...::test_benchmark_missing_directory_and_bad_names_never_read_files -q
FAILED ... AssertionError: must not read
```

Both temporary source mutations were restored exactly. `git diff --stat src/` shows only the pre-existing D1e tracked changes in `main.py` and `routes/demo.py`; no source fix-up changes remain.

Verification passed:

```text
make lint
make typecheck
make test
407 passed in 8.79s
```

Test count: 407 → 407.