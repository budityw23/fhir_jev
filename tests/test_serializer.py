"""Unit tests for pure FHIR R4-to-Jev serializers."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from fhir.resources.R4B import get_fhir_model_class
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.patient import Patient
from pydantic import ValidationError
from pydantic.v1 import ValidationError as PydanticV1ValidationError

from jev_fhir.serializer import (
    BundleSerializer,
    ConditionSerializer,
    ObservationSerializer,
    PatientSerializer,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> dict[str, Any]:
    """Load one checked-in JSON fixture."""
    return cast(dict[str, Any], json.loads((FIXTURES / relative_path).read_text()))


def test_all_phase_two_fixtures_are_valid_fhir_r4() -> None:
    Patient.parse_obj(load_fixture("patients/complete_patient.json"))
    Patient.parse_obj(load_fixture("patients/minimal_patient.json"))
    Patient.parse_obj(load_fixture("patients/invalid_nik.json"))
    Condition.parse_obj(load_fixture("conditions/dengue_a90.json"))
    Condition.parse_obj(load_fixture("conditions/common_cold_j06.json"))
    Bundle.parse_obj(load_fixture("bundles/lab_bundle.json"))
    Bundle.parse_obj(load_fixture("bundles/mixed_bundle.json"))


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURES.rglob("*.json")),
    ids=lambda path: str(path.relative_to(FIXTURES)),
)
def test_every_fixture_is_valid_fhir_r4(fixture_path: Path) -> None:
    resource = json.loads(fixture_path.read_text())

    get_fhir_model_class(resource["resourceType"]).parse_obj(resource)


def test_patient_complete_shape_matches_phase_spec() -> None:
    result = PatientSerializer().serialize(load_fixture("patients/complete_patient.json"))

    assert result == {
        "resource_type": "Patient",
        "has_identifier": True,
        "identifier_system": "nik",
        "identifier_value_length": 16,
        "has_name": True,
        "name_family": "Wijaya",
        "has_birth_date": True,
        "has_gender": True,
        "has_address": True,
        "address_country": "ID",
        "has_telecom": False,
        "telecom_count": 0,
        "field_completeness": 8,
        "field_total": 10,
    }


def test_patient_minimal_handles_missing_fields() -> None:
    result = PatientSerializer().serialize(load_fixture("patients/minimal_patient.json"))

    assert result["has_identifier"] is False
    assert result["identifier_system"] is None
    assert result["identifier_value_length"] is None
    assert result["has_name"] is False
    assert result["field_completeness"] == 0


def test_patient_retains_invalid_nik_for_a_later_decision_gate() -> None:
    result = PatientSerializer().serialize(load_fixture("patients/invalid_nik.json"))

    assert result["identifier_value_length"] == 15


def test_condition_extracts_icd10_and_statuses() -> None:
    result = ConditionSerializer().serialize(load_fixture("conditions/dengue_a90.json"))

    assert result == {
        "resource_type": "Condition",
        "code_system": "http://hl7.org/fhir/sid/icd-10",
        "code_value": "A90",
        "code_display": "Dengue fever [classical dengue]",
        "code_text": None,
        "clinical_status": "active",
        "verification_status": "confirmed",
        "has_subject": True,
        "has_onset": True,
        "category": "encounter-diagnosis",
    }


def test_condition_handles_missing_optional_fields() -> None:
    result = ConditionSerializer().serialize(load_fixture("conditions/common_cold_j06.json"))

    assert result["code_value"] == "J06.9"
    assert result["category"] is None
    assert result["has_onset"] is False


def test_condition_text_only_keeps_text_and_null_coded_fields() -> None:
    """Free text reaches the flat state without inventing a coding."""
    condition = load_fixture("conditions/dengue_a90.json")
    condition["code"] = {"text": "Demam berdarah dengue (DBD)"}

    result = ConditionSerializer().serialize(condition)

    assert result["code_text"] == condition["code"]["text"]
    assert result["code_system"] is None
    assert result["code_value"] is None
    assert result["code_display"] is None


def test_condition_keeps_coding_and_text() -> None:
    """Coding display remains distinct from the free text label."""
    condition = load_fixture("conditions/dengue_a90.json")
    condition["code"]["text"] = "Demam berdarah dengue (DBD)"

    result = ConditionSerializer().serialize(condition)

    assert result["code_text"] == condition["code"]["text"]
    assert result["code_system"] == "http://hl7.org/fhir/sid/icd-10"
    assert result["code_value"] == "A90"
    assert result["code_display"] == "Dengue fever [classical dengue]"


def test_condition_without_code_has_no_text() -> None:
    """An absent optional code does not produce free text."""
    condition = load_fixture("conditions/dengue_a90.json")
    del condition["code"]

    assert ConditionSerializer().serialize(condition)["code_text"] is None


@pytest.mark.parametrize("length", [200, 250])
def test_condition_code_text_is_limited_to_200_characters(length: int) -> None:
    """The boundary preserves characters, including multibyte Unicode text."""
    condition = load_fixture("conditions/dengue_a90.json")
    text = "é" * length
    condition["code"] = {"text": text}

    result = ConditionSerializer().serialize(condition)

    assert result["code_text"] == text[:200]
    assert len(result["code_text"]) == 200


@pytest.mark.parametrize("text", [123, True, [], {}])
def test_condition_rejects_non_string_code_text(text: object) -> None:
    """FHIR validation rejects non-string text before extraction."""
    condition = load_fixture("conditions/dengue_a90.json")
    condition["code"] = {"text": text}

    with pytest.raises(ValidationError, match=r"code\.text"):
        Condition.parse_obj(condition)
    with pytest.raises(ValidationError, match=r"code\.text"):
        ConditionSerializer().serialize(condition)


def test_condition_rejects_invalid_fhir_resource() -> None:
    with pytest.raises((ValidationError, PydanticV1ValidationError)):
        ConditionSerializer().serialize({"resourceType": "Patient"})


def test_observation_extracts_quantity_value() -> None:
    observation = load_fixture("bundles/lab_bundle.json")["entry"][0]["resource"]
    result = ObservationSerializer().serialize(observation)

    assert result["code_system"] == "http://loinc.org"
    assert result["code_value"] == "2951-2"
    assert result["value"] == 140
    assert result["value_type"] == "quantity"
    assert result["value_unit"] == "mmol/L"


def test_observation_extracts_string_value() -> None:
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"text": "Clinical note"},
        "valueString": "normal",
    }
    result = ObservationSerializer().serialize(observation)

    assert result["value"] == "normal"
    assert result["value_type"] == "string"
    assert result["value_unit"] is None


def test_observation_handles_missing_optional_references() -> None:
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"text": "Clinical note"},
    }
    result = ObservationSerializer().serialize(observation)

    assert result["has_subject"] is False
    assert result["has_encounter"] is False
    assert result["value"] is None


def test_bundle_extracts_lab_routing_signals() -> None:
    result = BundleSerializer().serialize(load_fixture("bundles/lab_bundle.json"))

    assert result["bundle_type"] == "collection"
    assert result["entry_count"] == 2
    assert result["entry_resource_types"] == ["Observation", "Observation"]
    assert result["dominant_resource_type"] == "Observation"
    assert result["has_patient_reference"] is True
    assert result["contains_lab_codes"] is True
    assert result["contains_condition_codes"] is False


def test_bundle_extracts_mixed_resource_signals() -> None:
    result = BundleSerializer().serialize(load_fixture("bundles/mixed_bundle.json"))

    assert result["contains_condition_codes"] is True
    assert result["has_encounter_reference"] is True
    assert result["contains_immunization"] is False
    assert result["contains_medication"] is False


def test_bundle_handles_empty_entries() -> None:
    result = BundleSerializer().serialize({"resourceType": "Bundle", "type": "collection"})

    assert result["entry_count"] == 0
    assert result["entry_resource_types"] == []
    assert result["dominant_resource_type"] is None


@pytest.mark.parametrize("has_encounter", [True, False])
def test_bundle_contains_encounter_tracks_entries(has_encounter: bool) -> None:
    """An Encounter entry alone determines the explicit encounter signal."""
    bundle = load_fixture("bundles/encounter_bundle.json")
    if not has_encounter:
        bundle["entry"] = bundle["entry"][1:]

    state = BundleSerializer().serialize(bundle)

    assert state["contains_encounter"] is has_encounter


def test_bundle_contains_encounter_when_conditions_dominate() -> None:
    """Eight Conditions do not hide the single Encounter entry."""
    bundle = load_fixture("bundles/encounter_bundle.json")
    encounter, condition = bundle["entry"]
    bundle["entry"] = [encounter] + [condition] * 8

    state = BundleSerializer().serialize(bundle)

    assert state["entry_resource_types"].count("Condition") == 8
    assert state["entry_resource_types"].count("Encounter") == 1
    assert state["contains_encounter"] is True
    assert state["dominant_resource_type"] == "Condition"


def test_bundle_encounter_reference_without_entry() -> None:
    """A reference does not imply that the Bundle contains an Encounter."""
    bundle = load_fixture("bundles/encounter_bundle.json")
    bundle["entry"] = bundle["entry"][1:]

    state = BundleSerializer().serialize(bundle)

    assert state["contains_encounter"] is False
    assert state["has_encounter_reference"] is True
