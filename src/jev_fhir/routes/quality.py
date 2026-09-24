"""Quality-score API endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from jev_fhir.config import Settings
from jev_fhir.dependencies import get_quality_scorer, get_settings_dep
from jev_fhir.metrics import record_decision
from jev_fhir.modules.quality_scorer import QualityScorer, QualityScoreResponse

router = APIRouter(tags=["quality"])


class QualityScoreRequest(BaseModel):
    """Request body for scoring a FHIR Patient or Observation."""

    resource_type: str
    resource: dict[str, Any]
    threshold: int | None = Field(default=None, ge=0, le=100)


@router.post("/quality-score", response_model=QualityScoreResponse)
async def quality_score(
    body: QualityScoreRequest,
    scorer: Annotated[QualityScorer, Depends(get_quality_scorer)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> QualityScoreResponse:
    """Return a data-quality decision for a raw FHIR resource."""
    threshold = body.threshold if body.threshold is not None else settings.quality_threshold_default
    response = await scorer.score(body.resource, body.resource_type, threshold)
    record_decision("quality_scorer", response.action, response.confidence)
    return response
