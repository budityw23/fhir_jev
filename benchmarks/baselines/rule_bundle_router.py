"""Rule baseline for routing FHIR Bundles."""

from typing import Any

from jev_fhir.modules.bundle_router import ROUTE_OPTIONS
from jev_fhir.serializer.bundle import BundleSerializer


def route_bundle(bundle: dict[str, Any]) -> str:
    """Route using documented resource-type and LOINC signals."""
    state = BundleSerializer().serialize(bundle)
    entry_count = int(state["entry_count"])
    resource_types = state["entry_resource_types"]
    observation_count = (
        resource_types.count("Observation") if isinstance(resource_types, list) else 0
    )
    if entry_count and observation_count / entry_count > 0.5 and state["contains_lab_codes"]:
        return "lab_result"
    if state["has_encounter_reference"]:
        return "encounter_summary"
    if state["contains_immunization"]:
        return "immunization_report"
    if state["contains_medication"]:
        return "medication_dispense"
    return "unknown"


def route_options() -> list[str]:
    """Expose the same fixed enum used by the Jev route module."""
    return ROUTE_OPTIONS.copy()
