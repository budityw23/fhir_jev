"""FHIR Observation serializer."""

from typing import Any

from fhir.resources.observation import Observation

from jev_fhir.serializer.base import FHIRSerializer, first_coding_code, first_coding_value


class ObservationSerializer(FHIRSerializer):
    """Flatten a clinical observation while preserving its value kind."""

    def resource_type(self) -> str:
        return "Observation"

    def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Validate an Observation and extract the requested fields."""
        Observation.parse_obj(resource)
        value_quantity = resource.get("valueQuantity")
        quantity_value = value_quantity.get("value") if isinstance(value_quantity, dict) else None
        quantity_unit = value_quantity.get("unit") if isinstance(value_quantity, dict) else None
        value_string = resource.get("valueString")
        value_type = (
            "quantity"
            if isinstance(value_quantity, dict)
            else "string"
            if isinstance(value_string, str)
            else None
        )

        return {
            "resource_type": self.resource_type(),
            "code_system": first_coding_value(resource.get("code"), "system"),
            "code_value": first_coding_code(resource.get("code")),
            "code_display": first_coding_value(resource.get("code"), "display"),
            "status": resource.get("status") if isinstance(resource.get("status"), str) else None,
            "value": quantity_value
            if value_type == "quantity"
            else value_string
            if value_type == "string"
            else None,
            "value_type": value_type,
            "value_unit": quantity_unit if isinstance(quantity_unit, str) else None,
            "effective_datetime": resource.get("effectiveDateTime")
            if isinstance(resource.get("effectiveDateTime"), str)
            else None,
            "has_subject": isinstance(resource.get("subject"), dict),
            "has_encounter": isinstance(resource.get("encounter"), dict),
        }
