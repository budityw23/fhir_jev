"""D1a tests for schemas and the allow-listed fixture catalog."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from jev_fhir.config import Settings
from jev_fhir.dataset.labels import LabelBase, NotifiableLabel, QualityLabel, RouteLabel
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.schemas import ThresholdOverrides, Thresholds

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "benchmarks/dataset/labels"


def catalog() -> FixtureCatalog:
    return FixtureCatalog(LABELS)


def label_rows() -> dict[str, list[dict[str, Any]]]:
    """Raw label files keyed by demo module, read independently of the catalog."""
    return {
        module: json.loads((LABELS / filename).read_text())
        for module, filename in (
            ("quality", "quality.json"),
            ("router", "bundle_routes.json"),
            ("notifiable", "notifiable.json"),
        )
    }


def test_catalog_totals_filters_and_root_relative_ids() -> None:
    value = catalog()
    rows = label_rows()
    all_rows = [row for module_rows in rows.values() for row in module_rows]
    entries = value.entries()
    assert len(entries) == len(all_rows)
    for module, module_rows in rows.items():
        assert len(value.entries(module=module)) == len(module_rows)  # type: ignore[arg-type]
    for source in ("unit", "hard", "generated", "demo"):
        expected = sum(row["source"] == source for row in all_rows)
        assert len(value.entries(source=source)) == expected
    for difficulty in ("easy", "hard"):
        expected = sum(row["difficulty"] == difficulty for row in all_rows)
        assert len(value.entries(difficulty=difficulty)) == expected
    assert [entry.id for entry in entries] == [row["fixture"] for row in all_rows]
    assert all(not entry.id.startswith("/") and ".." not in entry.id for entry in entries)


def test_load_resource_returns_the_labelled_fixture() -> None:
    value = catalog()
    fixture_id = "tests/fixtures/patients/complete_patient.json"
    resource = value.load_resource(fixture_id)
    assert resource == json.loads((ROOT / fixture_id).read_text())
    entry = value.get(fixture_id)
    assert (
        entry is not None and entry.resource_type == "Patient" and entry.name == "complete_patient"
    )


def test_ground_truth_is_label_minus_fixture_source_difficulty() -> None:
    value = catalog()
    models: dict[str, type[LabelBase]] = {
        "quality": QualityLabel,
        "router": RouteLabel,
        "notifiable": NotifiableLabel,
    }
    for module, module_rows in label_rows().items():
        for row in module_rows:
            entry = value.get(row["fixture"])
            assert entry is not None
            expected = (
                models[module]
                .model_validate(row)
                .model_dump(mode="json", exclude={"fixture", "source", "difficulty"})
            )
            assert entry.ground_truth == expected
            assert "rationale" in entry.ground_truth and "approved_by" in entry.ground_truth


def test_quality_label_marks_nik_expectation() -> None:
    value = catalog()
    labels = {
        "tests/fixtures/patients/complete_patient.json": "NIK ✓",
        "tests/fixtures/patients/invalid_nik.json": "NIK ✗",
    }
    for fixture_id, marker in labels.items():
        entry = value.get(fixture_id)
        assert entry is not None and entry.label.endswith(marker)
    observation = value.get("tests/fixtures/observations/missing_value.json")
    assert observation is not None and "NIK" not in observation.label


def test_catalog_get_unknown_and_labels() -> None:
    value = catalog()
    assert value.get("nope") is None
    assert all(entry.label for entry in value.entries())


def test_unknown_and_traversal_never_open_files() -> None:
    value = catalog()
    with patch("pathlib.Path.read_text", side_effect=AssertionError("must not read")):
        for fixture_id in ("../../.env", "tests/fixtures/../../.env"):
            with pytest.raises(KeyError):
                value.load_resource(fixture_id)


def test_approved_mirrors_labels() -> None:
    value = catalog()
    for module_rows in label_rows().values():
        for row in module_rows:
            entry = value.get(row["fixture"])
            assert entry is not None
            assert entry.approved is (row.get("approved_by") is not None)


def test_thresholds_validate_bounds_and_order() -> None:
    with pytest.raises(ValidationError):
        Thresholds(
            quality_threshold=70,
            route_confidence_minimum=0.5,
            notifiable_confirmed=0.5,
            notifiable_review=0.6,
        )
    with pytest.raises(ValidationError):
        Thresholds(
            quality_threshold=101,
            route_confidence_minimum=0.5,
            notifiable_confirmed=0.8,
            notifiable_review=0.5,
        )


def test_overrides_revalidate_and_from_settings() -> None:
    base = Thresholds.from_settings(
        Settings(
            quality_threshold_default=71,
            route_confidence_minimum=0.6,
            notifiable_confidence_minimum=0.9,
            notifiable_review_minimum=0.4,
        )
    )
    assert base.model_dump() == {
        "quality_threshold": 71,
        "route_confidence_minimum": 0.6,
        "notifiable_confirmed": 0.9,
        "notifiable_review": 0.4,
    }
    assert ThresholdOverrides(quality_threshold=80).apply(base).quality_threshold == 80
    with pytest.raises(ValidationError):
        ThresholdOverrides(notifiable_review=0.95).apply(base)
