"""Transparent rule baseline for FHIR Patient quality scoring."""

from typing import Any

from jev_fhir.serializer.patient import PatientSerializer


def score_patient(resource: dict[str, Any]) -> dict[str, int | bool | None]:
    """Score present demographic fields and check a 16-digit NIK with a regex-free rule."""
    state = PatientSerializer().serialize(resource)
    identifier_length = state["identifier_value_length"]
    nik_valid = identifier_length == 16 if isinstance(identifier_length, int) else None
    return {
        "score": round(100 * int(state["field_completeness"]) / int(state["field_total"])),
        "nik_valid": nik_valid,
    }
