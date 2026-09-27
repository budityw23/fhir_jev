PYTHON ?= .venv/bin/python
NODE_BIN ?= $(HOME)/.nvm/versions/node/v20.19.0/bin

.PHONY: lint typecheck test bench bench-live bench-full bench-live-full dataset dataset-check smoke-live serve web-install web-dev web-build web-types demo web-test web-e2e

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
	$(PYTHON) -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000

web-install:
	PATH="$(NODE_BIN):$$PATH"; cd web && npm ci

web-dev:
	PATH="$(NODE_BIN):$$PATH"; cd web && npm run dev

web-build:
	PATH="$(NODE_BIN):$$PATH"; cd web && npm run build

web-types:
	PATH="$(NODE_BIN):$$PATH"; $(PYTHON) scripts/dump_openapi.py && $(PYTHON) scripts/dump_openapi.py --samples && cd web && npm run types

demo:
	$(MAKE) web-build && DEMO_ENABLED=true $(PYTHON) -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000

web-test:
	PATH="$(NODE_BIN):$$PATH"; cd web && npm run lint && npm run typecheck && npm run test

web-e2e:
	PATH="$(NODE_BIN):$$PATH"; cd web && npm run e2e
