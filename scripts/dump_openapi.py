"""Write deterministic OpenAPI and recorded mock comparison samples for the web client."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from jev_fhir.config import PROJECT_ROOT, Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.compare import Comparer
from jev_fhir.demo.schemas import CompareRequest, ThresholdOverrides, Thresholds
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.main import create_app

WEB_DIR = PROJECT_ROOT / "web"
FIXTURES_DIR = WEB_DIR / "src" / "test" / "fixtures"


def _write_json(path: Path, value: Any) -> None:
    """Write sorted, indented JSON with one trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stable(value: Any, key: str | None = None) -> Any:
    """Replace volatile timings and timestamps recursively with stable sample values."""
    if key == "latency_ms":
        return 0.0
    if key in {"recorded", "timestamp"}:
        return "2000-01-01T00:00:00Z"
    if isinstance(value, dict):
        return {name: _stable(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


async def _write_samples() -> None:
    """Run the specified mock comparisons and serialize their deterministic responses."""
    settings = Settings(mock_jev=True, demo_enabled=True)
    catalog = FixtureCatalog(settings.labels_dir)
    comparer = Comparer(
        MockJevClient(),
        catalog,
        Thresholds.from_settings(settings),
        PROJECT_ROOT / "data" / "notifiable_diseases.json",
    )
    cases = (
        ("quality", "tests/fixtures/patients/complete_patient.json", None),
        (
            "router",
            "tests/fixtures/bundles/mixed_bundle.json",
            ThresholdOverrides(route_confidence_minimum=0.99),
        ),
        ("notifiable", "tests/fixtures/conditions/japanese_encephalitis_a83.json", None),
    )
    for module, fixture_id, thresholds in cases:
        request = CompareRequest(
            resource=catalog.load_resource(fixture_id),
            fixture_id=fixture_id,
            thresholds=thresholds,
        )
        response = await comparer.compare(module, request)  # type: ignore[arg-type]
        _write_json(
            FIXTURES_DIR / f"compare_{module}.json",
            _stable(response.model_dump(mode="json")),
        )


def main() -> None:
    """Parse options and write OpenAPI, or additionally write comparison samples."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", action="store_true")
    args = parser.parse_args()
    if args.samples:
        asyncio.run(_write_samples())
        return
    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    _write_json(WEB_DIR / "openapi.json", app.openapi())


if __name__ == "__main__":
    main()
