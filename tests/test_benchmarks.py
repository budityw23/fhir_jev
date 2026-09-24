"""Regression tests for the Phase 5 fixture corpus and benchmark harness."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.bench_runner import GROUND_TRUTH, async_main  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def load_labels(filename: str) -> set[str]:
    """Load fixture names from one ground-truth file."""
    entries = cast(list[dict[str, Any]], json.loads((GROUND_TRUTH / filename).read_text()))
    return {str(entry["fixture"]) for entry in entries}


def fixture_names(directory: str) -> set[str]:
    """Return fixture paths relative to the fixture root."""
    return {f"{directory}/{path.name}" for path in (FIXTURES / directory).glob("*.json")}


def test_phase_five_fixture_targets_and_labels_are_complete() -> None:
    patients = fixture_names("patients")
    conditions = fixture_names("conditions")
    bundles = fixture_names("bundles")

    assert len(patients) >= 20
    assert len(conditions) >= 15
    assert len(bundles) >= 15
    assert patients == load_labels("quality_scores.json")
    assert conditions == load_labels("notifiable_diseases.json")
    assert bundles == load_labels("bundle_routes.json")


def test_benchmark_runner_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    json_path, markdown_path = asyncio.run(async_main(tmp_path))

    report = cast(dict[str, Any], json.loads(json_path.read_text()))
    assert markdown_path.read_text().startswith("# Jev × FHIR Benchmark Report")
    assert report["mode"] == "mock_jev"
    assert report["modules"]["quality_scorer"]["fixture_count"] >= 20
    assert report["modules"]["bundle_router"]["fixture_count"] >= 15
    assert report["modules"]["notifiable_detector"]["fixture_count"] >= 15
