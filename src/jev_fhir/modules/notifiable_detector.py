"""Indonesian notifiable-disease detection module."""

import json
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel

from jev_fhir.fhir_helpers.flag_builder import FlagBuilder
from jev_fhir.jev_client.client import JevClient
from jev_fhir.logger import log_decision
from jev_fhir.serializer.condition import ConditionSerializer

NOTIFIABLE_STATEMENT = (
    "This condition is a notifiable disease that requires mandatory reporting to "
    "Indonesian public health authorities"
)


class NotifiableDetectionResponse(BaseModel):
    """Structured result returned by the notifiable-disease detector."""

    is_notifiable: bool
    probability: float
    status: str
    condition_code: str
    condition_display: str
    flag_resource: dict[str, Any] | None
    latency_ms: float


class NotifiableDiseaseDetector:
    """Assess a raw Condition and create a Flag for confirmed cases."""

    def __init__(
        self,
        jev_client: JevClient,
        serializer: ConditionSerializer | None = None,
        flag_builder: FlagBuilder | None = None,
        disease_data_path: Path | None = None,
    ) -> None:
        self._jev_client = jev_client
        self._serializer = serializer or ConditionSerializer()
        self._flag_builder = flag_builder or FlagBuilder()
        self._disease_data_path = disease_data_path or (
            Path(__file__).resolve().parents[3] / "data" / "notifiable_diseases.json"
        )

    async def detect(
        self,
        condition: dict[str, Any],
        confirmed_threshold: float = 0.8,
        review_threshold: float = 0.5,
    ) -> NotifiableDetectionResponse:
        """Classify a Condition and return a Flag only for confirmed positives."""
        if condition.get("resourceType") != "Condition":
            raise ValueError("notifiable detection requires a Condition resource")
        started_at = perf_counter()
        serialized = self._serializer.serialize(condition)
        state = {**serialized, "notifiable_diseases_context": self._disease_context()}
        result = await self._jev_client.noul(state, NOTIFIABLE_STATEMENT)

        if result.probability >= confirmed_threshold and result.answer:
            status = "confirmed_notifiable"
            is_notifiable = True
            subject = condition.get("subject")
            subject_reference = (
                subject.get("reference") if isinstance(subject, dict) else "Patient/unknown"
            )
            flag_resource = self._flag_builder.build(
                condition_code=serialized["code_value"] or "unknown",
                condition_display=serialized["code_display"] or "Unknown condition",
                subject_reference=subject_reference
                if isinstance(subject_reference, str)
                else "Patient/unknown",
                detection_date=date.today(),
            )
        elif result.probability >= review_threshold:
            status = "review_needed"
            is_notifiable = False
            flag_resource = None
        else:
            status = "not_notifiable"
            is_notifiable = False
            flag_resource = None

        response = NotifiableDetectionResponse(
            is_notifiable=is_notifiable,
            probability=result.probability,
            status=status,
            condition_code=serialized["code_value"] or "unknown",
            condition_display=serialized["code_display"] or "Unknown condition",
            flag_resource=flag_resource,
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
        )
        log_decision(
            module="notifiable_detector",
            resource_reference=f"Condition/{condition.get('id', 'unknown')}",
            decision=response.status,
            confidence=response.probability,
            latency_ms=response.latency_ms,
        )
        return response

    def _disease_context(self) -> list[dict[str, object]]:
        with self._disease_data_path.open(encoding="utf-8") as data_file:
            data = json.load(data_file)
        diseases = data.get("diseases")
        if not isinstance(diseases, list):
            raise ValueError("notifiable disease data must contain a diseases list")
        return [disease for disease in diseases if isinstance(disease, dict)]
