"""FHIR Condition serializer."""

from typing import Any

from fhir.resources.condition import Condition

from jev_fhir.serializer.base import FHIRSerializer, first_coding_code, first_coding_value


class ConditionSerializer(FHIRSerializer):
    """Flatten a Condition's coding, statuses, and clinical references."""

    def resource_type(self) -> str:
        return "Condition"

    def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Validate a Condition and extract its decision-relevant fields."""
        Condition.parse_obj(resource)
        code = resource.get("code")
        onset = resource.get("onsetDateTime")

        return {
            "resource_type": self.resource_type(),
            "code_system": first_coding_value(code, "system"),
            "code_value": first_coding_code(code),
            "code_display": first_coding_value(code, "display"),
            "clinical_status": first_coding_code(resource.get("clinicalStatus")),
            "verification_status": first_coding_code(resource.get("verificationStatus")),
            "has_subject": isinstance(resource.get("subject"), dict),
            "has_onset": isinstance(onset, str) or isinstance(resource.get("onsetPeriod"), dict),
            "category": first_coding_code(resource.get("category")),
        }
