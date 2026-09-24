"""Notifiable-disease detection API endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from jev_fhir.config import Settings
from jev_fhir.dependencies import get_notifiable_detector, get_settings_dep
from jev_fhir.metrics import record_decision
from jev_fhir.modules.notifiable_detector import (
    NotifiableDetectionResponse,
    NotifiableDiseaseDetector,
)

router = APIRouter(tags=["notifiable"])


class NotifiableDetectRequest(BaseModel):
    """Request body for detecting a notifiable FHIR Condition."""

    condition: dict[str, Any]


@router.post("/detect-notifiable", response_model=NotifiableDetectionResponse)
async def detect_notifiable(
    body: NotifiableDetectRequest,
    detector: Annotated[NotifiableDiseaseDetector, Depends(get_notifiable_detector)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> NotifiableDetectionResponse:
    """Detect reportable disease conditions and return a Flag when confirmed."""
    response = await detector.detect(
        body.condition,
        confirmed_threshold=settings.notifiable_confidence_minimum,
        review_threshold=settings.notifiable_review_minimum,
    )
    record_decision("notifiable_detector", response.status, response.probability)
    return response
