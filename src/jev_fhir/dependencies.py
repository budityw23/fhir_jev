"""FastAPI dependency providers for application-scoped decision modules."""

from dataclasses import dataclass

from fastapi import Request

from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer


@dataclass(frozen=True)
class AppServices:
    """Fully initialized dependencies required by API routes."""

    quality_scorer: QualityScorer
    bundle_router: BundleRouter
    notifiable_detector: NotifiableDiseaseDetector
    jev_client_kind: str


def get_services(request: Request) -> AppServices:
    """Get the initialized services from the current application instance."""
    return request.app.state.services  # type: ignore[no-any-return]


def get_quality_scorer(request: Request) -> QualityScorer:
    """Inject the QualityScorer without module-level mutable state."""
    return get_services(request).quality_scorer


def get_bundle_router(request: Request) -> BundleRouter:
    """Inject the BundleRouter without module-level mutable state."""
    return get_services(request).bundle_router


def get_notifiable_detector(request: Request) -> NotifiableDiseaseDetector:
    """Inject the NotifiableDiseaseDetector without module-level mutable state."""
    return get_services(request).notifiable_detector
