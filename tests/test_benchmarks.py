"""Regression tests for D0 labels and the benchmark harness."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.bench_runner import async_main  # noqa: E402
from jev_fhir.dataset.labels import QualityLabel, load_labels  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
LABELS = ROOT / "benchmarks" / "dataset" / "labels"
GROUND_TRUTH = ROOT / "benchmarks" / "ground_truth"


def fixture_names(directory: str) -> set[str]:
    return {f"{directory}/{path.name}" for path in (FIXTURES / directory).glob("*.json")}


def legacy_labels(filename: str) -> set[str]:
    entries = cast(list[dict[str, Any]], json.loads((GROUND_TRUTH / filename).read_text()))
    return {str(entry["fixture"]) for entry in entries}


def test_unit_fixture_targets_and_d0_labels_are_complete() -> None:
    patients = fixture_names("patients")
    assert len(patients) >= 20
    quality_labels = load_labels(LABELS / "quality.json", QualityLabel)
    assert {
        Path(label.fixture).relative_to("tests/fixtures").as_posix() for label in quality_labels
    } == patients
    assert all(
        label.expected_score_range[1] - label.expected_score_range[0] >= 20
        for label in quality_labels
    )
    assert all(label.rationale and label.approved_by is None for label in quality_labels)
    assert fixture_names("conditions") == legacy_labels("notifiable_diseases.json")
    assert fixture_names("bundles") == legacy_labels("bundle_routes.json")


def test_benchmark_runner_writes_d0_mock_report(tmp_path: Path) -> None:
    json_path, markdown_path = asyncio.run(async_main(tmp_path, limit=2))
    report = cast(dict[str, Any], json.loads(json_path.read_text()))
    assert markdown_path.read_text().startswith("# Jev × FHIR Benchmark Report")
    assert report["mode"] == "mock_jev"
    assert report["dataset"] == "unit"
    assert report["quality_labels_banded"] is True
    assert report["modules"]["quality_scorer"]["fixture_count"] == 2
