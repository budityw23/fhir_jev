"""Regression tests for D0 labels and the benchmark harness."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.bench_runner import async_main  # noqa: E402
from jev_fhir.dataset.labels import (  # noqa: E402
    NotifiableLabel,
    QualityLabel,
    RouteLabel,
    load_labels,
)

FIXTURES = ROOT / "tests" / "fixtures"
LABELS = ROOT / "benchmarks" / "dataset" / "labels"


def fixture_names(directory: str) -> set[str]:
    return {f"{directory}/{path.name}" for path in (FIXTURES / directory).glob("*.json")}


def test_unit_fixture_targets_and_d0_labels_are_complete() -> None:
    quality_targets = fixture_names("patients") | fixture_names("observations")
    assert len(quality_targets) >= 30
    quality_labels = [
        label
        for label in load_labels(LABELS / "quality.json", QualityLabel)
        if label.source == "unit"
    ]
    assert {
        Path(label.fixture).relative_to("tests/fixtures").as_posix() for label in quality_labels
    } == quality_targets
    assert all(
        label.expected_score_range[1] - label.expected_score_range[0] >= 20
        for label in quality_labels
    )
    assert all(label.rationale and label.approved_by is None for label in quality_labels)
    route_labels = load_labels(LABELS / "bundle_routes.json", RouteLabel)
    condition_labels = load_labels(LABELS / "notifiable.json", NotifiableLabel)
    assert {
        Path(label.fixture).relative_to("tests/fixtures").as_posix()
        for label in route_labels
        if label.source == "unit"
    } == fixture_names("bundles")
    assert {
        Path(label.fixture).relative_to("tests/fixtures").as_posix()
        for label in condition_labels
        if label.source == "unit"
    } == fixture_names("conditions")


def test_benchmark_runner_writes_d0_mock_report(tmp_path: Path) -> None:
    json_path, markdown_path = asyncio.run(async_main(tmp_path, limit=2))
    report = cast(dict[str, Any], json.loads(json_path.read_text()))
    assert markdown_path.read_text().startswith("# Jev × FHIR Benchmark Report")
    assert report["mode"] == "mock_jev"
    assert report["dataset"] == "unit"
    assert report["quality_labels_banded"] is True
    assert report["modules"]["quality_scorer"]["fixture_count"] == 2


def test_full_markdown_report_includes_breakdowns_and_approval_warning(tmp_path: Path) -> None:
    _, markdown_path = asyncio.run(async_main(tmp_path, dataset="full", limit=1))
    markdown = markdown_path.read_text()
    assert "### By source" in markdown
    assert "### By difficulty" in markdown
    assert "labels not yet approved by a human" in markdown
