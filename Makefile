.PHONY: lint typecheck test bench serve

lint:
	ruff check src tests benchmarks
	ruff format --check src tests benchmarks

typecheck:
	mypy --strict src tests benchmarks

test:
	pytest

bench:
	MOCK_JEV=true python -m benchmarks.bench_runner

serve:
	uvicorn jev_fhir.main:app --host 127.0.0.1 --port 8000
