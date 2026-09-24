"""FastAPI application for the Jev × FHIR decision layer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from pydantic.v1 import ValidationError as PydanticV1ValidationError

from jev_fhir.config import Settings, get_settings
from jev_fhir.dependencies import AppServices
from jev_fhir.jev_client.client import JevClient, JevClientError, LiveJevClient
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.logger import configure_logging
from jev_fhir.metrics import HTTP_LATENCY, HTTP_REQUESTS
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer
from jev_fhir.routes import metrics, notifiable, quality, routing


class ErrorResponse(BaseModel):
    """Consistent error body returned by all API exception handlers."""

    error: str
    detail: str | None = None
    request_id: str
    timestamp: datetime


def _error_response(
    request: Request, status_code: int, error: str, detail: str | None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = ErrorResponse(
        error=error,
        detail=detail,
        request_id=request_id,
        timestamp=datetime.now(UTC),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configurable application instance."""
    effective_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        jev_client: JevClient
        if effective_settings.mock_jev:
            jev_client = MockJevClient()
            client_kind = "mock"
        else:
            jev_client = LiveJevClient(
                api_key=effective_settings.jev_api_key,
                base_url=effective_settings.jev_base_url,
            )
            client_kind = "live"

        app.state.services = AppServices(
            quality_scorer=QualityScorer(jev_client),
            bundle_router=BundleRouter(jev_client),
            notifiable_detector=NotifiableDiseaseDetector(jev_client),
            jev_client_kind=client_kind,
        )
        yield
        if isinstance(jev_client, LiveJevClient):
            await jev_client.aclose()

    app = FastAPI(
        title="Jev × FHIR Decision Layer",
        version="0.1.0",
        description="Proof-of-concept: Jev AI decision primitives for FHIR clinical workflows",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: object) -> object:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-Id"] = request_id
        return response

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next: object) -> object:
        started_at = perf_counter()
        response = await call_next(request)  # type: ignore[operator]
        elapsed_seconds = perf_counter() - started_at
        endpoint = getattr(request.scope.get("route"), "path", request.url.path)
        HTTP_REQUESTS.labels(
            endpoint=endpoint, method=request.method, status=str(response.status_code)
        ).inc()
        HTTP_LATENCY.labels(endpoint=endpoint).observe(elapsed_seconds)
        response.headers["X-Request-Duration-Ms"] = f"{elapsed_seconds * 1000:.3f}"
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(request, 422, "validation_error", str(exc.errors()))

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(request, 422, "validation_error", str(exc.errors()))

    @app.exception_handler(PydanticV1ValidationError)
    async def pydantic_v1_validation_handler(
        request: Request, exc: PydanticV1ValidationError
    ) -> JSONResponse:
        return _error_response(request, 422, "validation_error", str(exc.errors()))

    @app.exception_handler(JevClientError)
    async def jev_error_handler(request: Request, exc: JevClientError) -> JSONResponse:
        return _error_response(request, 502, "jev_error", str(exc))

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return _error_response(request, 400, "invalid_request", str(exc))

    app.include_router(quality.router, prefix="/api/v1")
    app.include_router(routing.router, prefix="/api/v1")
    app.include_router(notifiable.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health(request: Request) -> dict[str, str]:
        """Report that the API has initialized its configured Jev client."""
        services: AppServices = request.app.state.services
        return {"status": "ok", "jev_client": services.jev_client_kind, "version": "0.1.0"}

    return app


app = create_app()
