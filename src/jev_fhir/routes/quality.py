"""Quality-score API endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from jev_fhir.dependencies import get_quality_scorer
from jev_fhir.metrics import record_decision
from jev_fhir.modules.quality_scorer import QualityScorer, QualityScoreResponse

router = APIRouter(tags=["quality"])


class QualityScoreRequest(BaseModel):
    """Request body for scoring a FHIR Patient or Observation."""

    resource_type: str
    resource: dict[str, Any]
    threshold: int = Field(default=70, ge=0, le=100)


@router.post("/quality-score", response_model=QualityScoreResponse)
async def quality_score(
    body: QualityScoreRequest,
    scorer: Annotated[QualityScorer, Depends(get_quality_scorer)],
) -> QualityScoreResponse:
    """Return a data-quality decision for a raw FHIR resource."""
    response = await scorer.score(body.resource, body.resource_type, body.threshold)
    record_decision("quality_scorer", response.action, response.confidence)
    return response
