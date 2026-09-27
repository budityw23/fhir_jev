"""D1b Compare API routes, mounted only when demo mode is enabled."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from jev_fhir.dataset.labels import Difficulty, Source
from jev_fhir.demo import DemoNotFoundError
from jev_fhir.demo.feed import DecisionEvent, event_from_compare
from jev_fhir.demo.pipeline import PipelineRunRequest, PipelineRunResponse
from jev_fhir.demo.schemas import (
    CompareRequest,
    CompareResponse,
    DemoConfig,
    DemoModule,
    FixtureEntry,
    Thresholds,
)
from jev_fhir.dependencies import DemoServices, get_demo
from jev_fhir.modules.bundle_router import ROUTE_OPTIONS, ROUTE_QUESTION
from jev_fhir.modules.notifiable_detector import NOTIFIABLE_STATEMENT
from jev_fhir.modules.quality_scorer import NIK_VALIDATION_STATEMENT, QUALITY_SCORE_QUESTION

router = APIRouter(tags=["demo"])
DemoDependency = Annotated[DemoServices, Depends(get_demo)]


@router.get("/config", response_model=DemoConfig)
async def get_config(request: Request, services: DemoDependency) -> DemoConfig:
    """Return the active demo configuration and module prompts."""
    app_services = request.app.state.services
    return DemoConfig(
        mode=app_services.jev_client_kind,
        jev_model=app_services.jev_model,
        thresholds=Thresholds.from_settings(app_services.settings),
        route_options=ROUTE_OPTIONS,
        questions={
            "QUALITY_SCORE_QUESTION": QUALITY_SCORE_QUESTION,
            "NIK_VALIDATION_STATEMENT": NIK_VALIDATION_STATEMENT,
            "ROUTE_QUESTION": ROUTE_QUESTION,
            "NOTIFIABLE_STATEMENT": NOTIFIABLE_STATEMENT,
        },
    )


@router.get("/fixtures", response_model=list[FixtureEntry])
async def get_fixtures(
    services: DemoDependency,
    module: DemoModule | None = None,
    source: Source | None = None,
    difficulty: Difficulty | None = None,
) -> list[FixtureEntry]:
    """List the filtered, allow-listed fixture catalog."""
    return services.catalog.entries(module=module, source=source, difficulty=difficulty)


@router.get("/fixtures/{fixture_id:path}")
async def get_fixture(fixture_id: str, services: DemoDependency) -> dict[str, object]:
    """Load an allow-listed FHIR resource without constructing user paths."""
    try:
        return services.catalog.load_resource(fixture_id)
    except KeyError as exc:
        raise DemoNotFoundError("fixture not found") from exc


@router.post("/compare/{module}", response_model=CompareResponse)
async def compare(
    module: DemoModule, body: CompareRequest, services: DemoDependency
) -> CompareResponse:
    """Compare a single FHIR resource through Jev and its rule baseline."""
    response = await services.comparer.compare(module, body)
    services.feed.publish(event_from_compare(response, run_id=None, fixture_id=body.fixture_id))
    return response


@router.get("/decisions", response_model=list[DecisionEvent])
async def get_decisions(
    services: DemoDependency, limit: int = Query(50, ge=1, le=500)
) -> list[DecisionEvent]:
    """Return recent decision events in descending sequence order."""
    return services.feed.recent(limit)


@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def run_pipeline(body: PipelineRunRequest, services: DemoDependency) -> PipelineRunResponse:
    """Start the finite labelled-fixture replay pipeline."""
    return await services.pipeline.start(body)


@router.post("/pipeline/{run_id}/stop")
async def stop_pipeline(run_id: str, services: DemoDependency) -> dict[str, bool]:
    """Stop the active named pipeline run, if it is still running."""
    return {"stopped": await services.pipeline.stop(run_id)}
