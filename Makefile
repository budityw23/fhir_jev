PYTHON ?= .venv/bin/python

.PHONY: lint typecheck test bench bench-live bench-full bench-live-full dataset dataset-check smoke-live serve

lint:
	$(PYTHON) -m ruff check src tests benchmarks
	$(PYTHON) -m ruff format --check src tests benchmarks

typecheck:
	$(PYTHON) -m mypy --strict src tests benchmarks

test:
	$(PYTHON) -m pytest

bench:
	MOCK_JEV=true $(PYTHON) -m benchmarks.bench_runner

bench-live:
	MOCK_JEV=false $(PYTHON) -m benchmarks.bench_runner --live

bench-full:
	MOCK_JEV=true $(PYTHON) -m benchmarks.bench_runner --dataset full

bench-live-full:
	MOCK_JEV=false $(PYTHON) -m benchmarks.bench_runner --live --dataset full

dataset:
	$(PYTHON) scripts/generate_dataset.py --seed 42

dataset-check:
	$(PYTHON) scripts/generate_dataset.py --check

smoke-live:
	MOCK_JEV=false $(PYTHON) scripts/smoke_live.py

serve:
	uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000
