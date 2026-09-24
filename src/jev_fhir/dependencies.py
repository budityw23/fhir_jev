"""FastAPI dependency providers for application-scoped services."""

from dataclasses import dataclass

from fastapi import HTTPException, Request

from jev_fhir.config import Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.jev_client.client import JevClient
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer


@dataclass(frozen=True)
class DemoServices:
    """Services behind the optional demo API; built only when demo mode is enabled."""

    catalog: FixtureCatalog


@dataclass(frozen=True)
class AppServices:
    """Fully initialized dependencies required by API routes."""

    quality_scorer: QualityScorer
    bundle_router: BundleRouter
    notifiable_detector: NotifiableDiseaseDetector
    jev_client_kind: str
    settings: Settings
    jev_client: JevClient
    jev_model: str | None
    demo: DemoServices | None


def get_services(request: Request) -> AppServices:
    """Get initialized services from application state."""
    return request.app.state.services  # type: ignore[no-any-return]


def get_settings_dep(request: Request) -> Settings:
    """Inject the active application settings."""
    return get_services(request).settings


def get_quality_scorer(request: Request) -> QualityScorer:
    return get_services(request).quality_scorer


def get_bundle_router(request: Request) -> BundleRouter:
    return get_services(request).bundle_router


def get_notifiable_detector(request: Request) -> NotifiableDiseaseDetector:
    return get_services(request).notifiable_detector


def get_demo(request: Request) -> DemoServices:
    """Get the optional demo service set, or report that its routes are unavailable."""
    demo = get_services(request).demo
    if demo is None:
        raise HTTPException(status_code=404, detail="not_found")
    return demo
