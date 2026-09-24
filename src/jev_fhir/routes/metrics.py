"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from jev_fhir.metrics import metrics_payload

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=Response)
async def metrics() -> Response:
    """Expose Prometheus-compatible counters and histograms."""
    payload, media_type = metrics_payload()
    return Response(content=payload, media_type=media_type)
