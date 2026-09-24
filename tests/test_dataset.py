"""D0.5 dataset integrity checks."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fhir.resources.R4B import get_fhir_model_class

from jev_fhir.dataset.labels import (
    LabelBase,
    NotifiableLabel,
    QualityLabel,
    RouteLabel,
    fixture_path,
    load_labels,
)

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "benchmarks/dataset/labels"
RESOURCE_FILES = sorted((ROOT / "tests/fixtures").rglob("*.json")) + sorted(
    path
    for directory in ("hard", "demo", "generated")
    for path in (ROOT / "benchmarks/dataset" / directory).rglob("*.json")
)


@pytest.mark.parametrize("path", RESOURCE_FILES)
def test_dataset_resources_are_valid_r4b(path: Path) -> None:
    resource = json.loads(path.read_text())
    get_fhir_model_class(resource["resourceType"]).model_validate(resource)


def test_labels_are_complete_unique_and_resolve() -> None:
    labels: list[LabelBase] = []
    labels.extend(load_labels(LABELS / "quality.json", QualityLabel))
    labels.extend(load_labels(LABELS / "bundle_routes.json", RouteLabel))
    labels.extend(load_labels(LABELS / "notifiable.json", NotifiableLabel))
    targets = [label.fixture for label in labels]
    assert len(targets) == len(set(targets))
    assert all(fixture_path(label).is_file() for label in labels)
    expected = {path.relative_to(ROOT).as_posix() for path in RESOURCE_FILES}
    assert set(targets) == expected


def test_d0_5_thresholds_and_discriminating_cases() -> None:
    routes = load_labels(LABELS / "bundle_routes.json", RouteLabel)
    conditions = load_labels(LABELS / "notifiable.json", NotifiableLabel)
    quality = load_labels(LABELS / "quality.json", QualityLabel)
    assert len(routes) >= 100 and len(conditions) >= 30 and len(quality) >= 50
    assert {label.expected_category for label in routes} == {
        "lab_result",
        "encounter_summary",
        "immunization_report",
        "medication_dispense",
        "unknown",
    }
    assert all(
        sum(label.expected_category == category for label in routes) >= 15
        for category in {label.expected_category for label in routes}
    )
    required = {
        "tb_subcode_a15_0.json",
        "malaria_subcode_b50_9.json",
        "typhoid_subcode_a01_0.json",
        "dengue_snomed_only.json",
        "tb_snomed_only.json",
        "dbd_text_only.json",
        "tb_paru_text_only.json",
    }
    assert required <= {Path(label.fixture).name for label in conditions}


def test_generator_check_passes() -> None:
    subprocess.run([sys.executable, "scripts/generate_dataset.py", "--check"], cwd=ROOT, check=True)


def test_hard_snomed_and_icd10_codings_are_well_formed() -> None:
    import re

    for path in (ROOT / "benchmarks/dataset/hard/conditions").glob("*.json"):
        codings = json.loads(path.read_text()).get("code", {}).get("coding", [])
        if path.name.endswith("_snomed_only.json"):
            assert codings and {coding.get("system") for coding in codings} == {
                "http://snomed.info/sct"
            }
        for coding in codings:
            if coding.get("system") == "http://hl7.org/fhir/sid/icd-10":
                assert re.fullmatch(r"[A-Z][0-9]{2}(\.[0-9A-Z]+)?", coding.get("code", ""))


def test_observation_baseline_handles_zero_and_quality_failures() -> None:
    from jev_fhir.baselines.quality import score_observation

    complete = json.loads((ROOT / "tests/fixtures/observations/complete_lab_hb.json").read_text())
    complete_score = score_observation(complete)["score"]
    assert isinstance(complete_score, int)
    assert complete_score > 70
    zero = json.loads((ROOT / "tests/fixtures/observations/complete_lab_hb.json").read_text())
    zero["valueQuantity"]["value"] = 0
    assert score_observation(zero)["score"] == complete_score
    for name in ("missing_value.json", "entered_in_error.json", "no_subject.json"):
        value = json.loads((ROOT / "tests/fixtures/observations" / name).read_text())
        score = score_observation(value)["score"]
        assert isinstance(score, int)
        assert score < complete_score


def test_easy_notifiable_labels_are_caught_by_exact_code_rules() -> None:
    """An "easy" confirmed case must use a code the reference list names exactly.

    Guards against demo/unit fixtures coded at the wrong ICD-10 level (e.g. A83 instead of A83.0).
    """
    from jev_fhir.baselines.notifiable import is_notifiable

    conditions = load_labels(LABELS / "notifiable.json", NotifiableLabel)
    easy_confirmed = [
        label
        for label in conditions
        if label.difficulty == "easy" and label.expected_status == "confirmed_notifiable"
    ]
    assert easy_confirmed
    for label in easy_confirmed:
        resource = json.loads(fixture_path(label).read_text())
        assert is_notifiable(resource, ROOT / "data/notifiable_diseases.json"), label.fixture


def test_generated_encounter_bundles_link_conditions_to_their_encounter() -> None:
    """Encounter summaries must be realistic: every Condition references the bundle's Encounter."""
    routes = load_labels(LABELS / "bundle_routes.json", RouteLabel)
    encounter_bundles = [
        label
        for label in routes
        if label.source == "generated" and label.expected_category == "encounter_summary"
    ]
    assert encounter_bundles
    for label in encounter_bundles:
        resources = [e["resource"] for e in json.loads(fixture_path(label).read_text())["entry"]]
        encounter_refs = {
            f"Encounter/{r['id']}" for r in resources if r["resourceType"] == "Encounter"
        }
        conditions = [r for r in resources if r["resourceType"] == "Condition"]
        assert encounter_refs and conditions, label.fixture
        for condition in conditions:
            assert condition.get("encounter", {}).get("reference") in encounter_refs, label.fixture
