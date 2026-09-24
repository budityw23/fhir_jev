"""FHIR Bundle routing decision module."""

from time import perf_counter
from typing import Any

from pydantic import BaseModel

from jev_fhir.jev_client.client import JevClient
from jev_fhir.logger import log_decision
from jev_fhir.serializer.bundle import BundleSerializer

ROUTE_QUESTION = "What type of clinical data does this FHIR Bundle primarily contain?"
ROUTE_OPTIONS = [
    "lab_result",
    "encounter_summary",
    "immunization_report",
    "medication_dispense",
    "unknown",
]


class BundleRouteResponse(BaseModel):
    """Structured result returned by the Bundle router."""

    category: str
    confidence: float
    probabilities: dict[str, float]
    bundle_id: str
    latency_ms: float


class BundleRouter:
    """Route a raw FHIR Bundle to a fixed downstream processing category."""

    def __init__(self, jev_client: JevClient, serializer: BundleSerializer | None = None) -> None:
        self._jev_client = jev_client
        self._serializer = serializer or BundleSerializer()

    async def route(
        self, bundle: dict[str, Any], confidence_minimum: float = 0.5
    ) -> BundleRouteResponse:
        """Select a route, overriding low-confidence decisions to ``unknown``."""
        started_at = perf_counter()
        state = self._serializer.serialize(bundle)
        result = await self._jev_client.choice(state, ROUTE_QUESTION, ROUTE_OPTIONS)
        category = result.choice if result.confidence >= confidence_minimum else "unknown"
        response = BundleRouteResponse(
            category=category,
            confidence=result.confidence,
            probabilities=result.probabilities,
            bundle_id=str(bundle.get("id", "unknown")),
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
        )
        log_decision(
            module="bundle_router",
            resource_reference=f"Bundle/{response.bundle_id}",
            decision=response.category,
            confidence=response.confidence,
            latency_ms=response.latency_ms,
        )
        return response
