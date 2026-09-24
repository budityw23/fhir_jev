"""FHIR resource quality scoring decision module."""

from time import perf_counter
from typing import Any

from pydantic import BaseModel

from jev_fhir.jev_client.client import JevClient
from jev_fhir.logger import log_decision
from jev_fhir.serializer.base import FHIRSerializer
from jev_fhir.serializer.observation import ObservationSerializer
from jev_fhir.serializer.patient import PatientSerializer

QUALITY_SCORE_QUESTION = (
    "Rate the data quality and completeness of this clinical resource from 0 "
    "(empty/invalid) to 100 (all fields present, correctly formatted, clinically complete)"
)
NIK_VALIDATION_STATEMENT = "This patient has a valid 16-digit Indonesian NIK identifier"


class QualityScoreResponse(BaseModel):
    """Structured result returned by the quality-scoring module."""

    score: int
    confidence: float
    level: str
    missing_fields: list[str]
    nik_valid: bool | None
    nik_confidence: float | None
    resource_reference: str
    latency_ms: float
    action: str


class QualityScorer:
    """Score a raw FHIR resource and optionally validate a Patient NIK."""

    def __init__(
        self, jev_client: JevClient, serializers: dict[str, FHIRSerializer] | None = None
    ) -> None:
        self._jev_client = jev_client
        self._serializers = serializers or {
            "Patient": PatientSerializer(),
            "Observation": ObservationSerializer(),
        }

    async def score(
        self, resource: dict[str, Any], resource_type: str, threshold: int = 70
    ) -> QualityScoreResponse:
        """Score one raw FHIR resource against the supplied acceptance threshold."""
        serializer = self._serializers.get(resource_type)
        if serializer is None:
            raise ValueError(f"Unsupported resource type for quality scoring: {resource_type}")
        if resource.get("resourceType") != resource_type:
            raise ValueError("resource_type does not match resource.resourceType")

        started_at = perf_counter()
        state = serializer.serialize(resource)
        score_result = await self._jev_client.score(state, QUALITY_SCORE_QUESTION)
        nik_valid: bool | None = None
        nik_confidence: float | None = None
        if resource_type == "Patient":
            nik_result = await self._jev_client.noul(state, NIK_VALIDATION_STATEMENT)
            nik_valid = nik_result.answer
            nik_confidence = nik_result.probability

        # The NIK check is a gate: a Patient whose NIK is judged invalid (or absent) goes to
        # review even when the completeness score passes the threshold.
        passes_nik_gate = nik_valid is not False
        action = (
            "auto_accept"
            if score_result.score >= threshold and passes_nik_gate
            else "review_needed"
        )
        response = QualityScoreResponse(
            score=score_result.score,
            confidence=score_result.confidence,
            level="acceptable" if action == "auto_accept" else "review_needed",
            missing_fields=self._missing_fields(resource_type, state),
            nik_valid=nik_valid,
            nik_confidence=nik_confidence,
            resource_reference=self._resource_reference(resource),
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
            action=action,
        )
        log_decision(
            module="quality_scorer",
            resource_reference=response.resource_reference,
            decision=response.action,
            confidence=response.confidence,
            latency_ms=response.latency_ms,
        )
        return response

    @staticmethod
    def _resource_reference(resource: dict[str, Any]) -> str:
        resource_type = resource.get("resourceType", "Resource")
        resource_id = resource.get("id", "unknown")
        return f"{resource_type}/{resource_id}"

    @staticmethod
    def _missing_fields(resource_type: str, state: dict[str, Any]) -> list[str]:
        if resource_type == "Patient":
            fields = {
                "has_identifier": "identifier",
                "has_name": "name",
                "has_birth_date": "birthDate",
                "has_gender": "gender",
                "has_address": "address",
                "has_telecom": "telecom",
            }
            return [name for key, name in fields.items() if not state[key]]
        return [key for key, value in state.items() if value is None]
