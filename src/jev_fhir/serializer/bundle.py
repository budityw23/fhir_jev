"""FHIR Bundle serializer."""

from collections import Counter
from collections.abc import Mapping
from typing import Any

from fhir.resources.bundle import Bundle

from jev_fhir.serializer.base import FHIRSerializer


def _walk_mappings(value: object) -> list[Mapping[str, Any]]:
    """Return every mapping nested in a JSON-compatible value."""
    if isinstance(value, Mapping):
        mapping_descendants = [value]
        for child in value.values():
            mapping_descendants.extend(_walk_mappings(child))
        return mapping_descendants
    if isinstance(value, list):
        list_descendants: list[Mapping[str, Any]] = []
        for child in value:
            list_descendants.extend(_walk_mappings(child))
        return list_descendants
    return []


class BundleSerializer(FHIRSerializer):
    """Flatten Bundle composition and reference signals for routing."""

    def resource_type(self) -> str:
        return "Bundle"

    def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Validate a Bundle and collect routing signals without external calls."""
        Bundle.parse_obj(resource)
        entries = resource.get("entry")
        entry_list = entries if isinstance(entries, list) else []
        entry_resources = [
            entry["resource"]
            for entry in entry_list
            if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
        ]
        resource_types = [
            nested["resourceType"]
            for nested in entry_resources
            if isinstance(nested.get("resourceType"), str)
        ]
        type_counts = Counter(resource_types)
        dominant_resource_type = type_counts.most_common(1)[0][0] if type_counts else None
        nested_values = _walk_mappings(entry_resources)
        references = [
            item["reference"] for item in nested_values if isinstance(item.get("reference"), str)
        ]
        coding_systems = [
            item["system"] for item in nested_values if isinstance(item.get("system"), str)
        ]

        return {
            "resource_type": self.resource_type(),
            "bundle_type": resource.get("type") if isinstance(resource.get("type"), str) else None,
            "entry_count": len(entry_list),
            "entry_resource_types": resource_types,
            "dominant_resource_type": dominant_resource_type,
            "has_patient_reference": any(
                reference.startswith("Patient/") for reference in references
            ),
            "has_encounter_reference": any(
                reference.startswith("Encounter/") for reference in references
            ),
            "contains_lab_codes": any(
                system.lower() == "http://loinc.org" for system in coding_systems
            ),
            "contains_condition_codes": "Condition" in resource_types,
            "contains_immunization": "Immunization" in resource_types,
            "contains_medication": "MedicationDispense" in resource_types,
        }
