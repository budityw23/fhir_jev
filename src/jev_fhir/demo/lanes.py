"""Pure lane-assignment policy for demo decisions."""

from pydantic import BaseModel

from jev_fhir.demo.schemas import DemoModule, Lane, Thresholds
from jev_fhir.modules.bundle_router import BundleRouteResponse
from jev_fhir.modules.notifiable_detector import NotifiableDetectionResponse
from jev_fhir.modules.quality_scorer import QualityScoreResponse


def assign_lane(
    module: DemoModule, response: BaseModel, thresholds: Thresholds, override_applied: bool
) -> tuple[Lane, str]:
    """Assign the exact presentation lane and reason for a Jev module response."""
    if module == "quality":
        quality = response if isinstance(response, QualityScoreResponse) else None
        if quality is None:
            raise TypeError("quality module requires QualityScoreResponse")
        if quality.action == "auto_accept":
            return (
                "auto_accepted",
                f"score {quality.score} ≥ threshold {thresholds.quality_threshold}",
            )
        if quality.score < thresholds.quality_threshold:
            return "review", f"score {quality.score} < threshold {thresholds.quality_threshold}"
        return "review", f"NIK gate failed: P(valid) {quality.nik_confidence:.2f}"
    if module == "router":
        router = response if isinstance(response, BundleRouteResponse) else None
        if router is None:
            raise TypeError("router module requires BundleRouteResponse")
        if router.category != "unknown":
            return "routed", f"{router.category} @ {router.confidence:.2f}"
        if override_applied:
            return (
                "review",
                f"confidence {router.confidence:.2f} < floor "
                f"{thresholds.route_confidence_minimum:.2f}",
            )
        return "review", "model chose unknown"
    detector = response if isinstance(response, NotifiableDetectionResponse) else None
    if detector is None:
        raise TypeError("notifiable module requires NotifiableDetectionResponse")
    if detector.status == "confirmed_notifiable":
        return (
            "flagged",
            f"P(notifiable) {detector.probability:.2f} ≥ {thresholds.notifiable_confirmed:.2f}",
        )
    if detector.status == "review_needed":
        return "review", f"P(notifiable) {detector.probability:.2f} in review band"
    return (
        "auto_accepted",
        f"P(notifiable) {detector.probability:.2f} < {thresholds.notifiable_review:.2f}",
    )
