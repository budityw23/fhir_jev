"""Common interface and validation helpers for FHIR resource serializers."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class FHIRSerializer(ABC):
    """Convert one FHIR R4 resource type into a flat decision state."""

    @abstractmethod
    def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Validate and extract the decision-relevant fields from a resource."""

    @abstractmethod
    def resource_type(self) -> str:
        """Return the FHIR resource type handled by this serializer."""


def first_mapping(value: object) -> Mapping[str, Any] | None:
    """Return the first mapping from a FHIR repeating element, if present."""
    if isinstance(value, list) and value and isinstance(value[0], Mapping):
        return value[0]
    return None


def first_coding_code(value: object) -> str | None:
    """Extract the first coding code from a FHIR CodeableConcept-like mapping."""
    if isinstance(value, list):
        value = first_mapping(value)
    if not isinstance(value, Mapping):
        return None
    coding = first_mapping(value.get("coding"))
    code = coding.get("code") if coding is not None else None
    return code if isinstance(code, str) else None


def first_coding_value(value: object, key: str) -> str | None:
    """Extract one string property from the first Coding element."""
    if isinstance(value, list):
        value = first_mapping(value)
    if not isinstance(value, Mapping):
        return None
    coding = first_mapping(value.get("coding"))
    result = coding.get(key) if coding is not None else None
    return result if isinstance(result, str) else None
