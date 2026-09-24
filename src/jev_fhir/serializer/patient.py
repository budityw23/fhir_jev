"""FHIR Patient serializer."""

from typing import Any

from fhir.resources.patient import Patient

from jev_fhir.serializer.base import FHIRSerializer, first_mapping


class PatientSerializer(FHIRSerializer):
    """Flatten a Patient into the identity and demographic fields Jev needs."""

    def resource_type(self) -> str:
        return "Patient"

    def serialize(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Validate a Patient and produce a missing-field-safe flat state."""
        Patient.parse_obj(resource)

        identifier = first_mapping(resource.get("identifier"))
        name = first_mapping(resource.get("name"))
        address = first_mapping(resource.get("address"))
        telecom = resource.get("telecom")

        identifier_system = identifier.get("system") if identifier is not None else None
        identifier_value = identifier.get("value") if identifier is not None else None
        name_family = name.get("family") if name is not None else None
        address_country = address.get("country") if address is not None else None

        has_identifier = identifier is not None
        has_name = name is not None
        has_birth_date = isinstance(resource.get("birthDate"), str)
        has_gender = isinstance(resource.get("gender"), str)
        has_address = address is not None
        has_telecom = isinstance(telecom, list) and bool(telecom)
        field_completeness = sum(
            (
                has_identifier,
                isinstance(identifier_system, str),
                isinstance(identifier_value, str),
                has_name,
                isinstance(name_family, str),
                has_birth_date,
                has_gender,
                has_address,
            )
        )

        return {
            "resource_type": self.resource_type(),
            "has_identifier": has_identifier,
            "identifier_system": identifier_system if isinstance(identifier_system, str) else None,
            "identifier_value_length": len(identifier_value)
            if isinstance(identifier_value, str)
            else None,
            "has_name": has_name,
            "name_family": name_family if isinstance(name_family, str) else None,
            "has_birth_date": has_birth_date,
            "has_gender": has_gender,
            "has_address": has_address,
            "address_country": address_country if isinstance(address_country, str) else None,
            "has_telecom": has_telecom,
            "telecom_count": len(telecom) if isinstance(telecom, list) else 0,
            "field_completeness": field_completeness,
            "field_total": 10,
        }
