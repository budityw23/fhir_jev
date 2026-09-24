"""FHIR Bundle routing API endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from jev_fhir.dependencies import get_bundle_router
from jev_fhir.metrics import record_decision
from jev_fhir.modules.bundle_router import BundleRouter, BundleRouteResponse

router = APIRouter(tags=["routing"])


class BundleRouteRequest(BaseModel):
    """Request body for routing a FHIR Bundle."""

    bundle: dict[str, Any]


@router.post("/route-bundle", response_model=BundleRouteResponse)
async def route_bundle(
    body: BundleRouteRequest,
    bundle_router: Annotated[BundleRouter, Depends(get_bundle_router)],
) -> BundleRouteResponse:
    """Route a raw FHIR Bundle to a declared processing category."""
    response = await bundle_router.route(body.bundle)
    record_decision("bundle_router", response.category, response.confidence)
    return response
