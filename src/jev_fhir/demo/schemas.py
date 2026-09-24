"""Typed contracts shared by the optional demo API."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from jev_fhir.config import Settings
from jev_fhir.dataset.labels import Difficulty, Source
from jev_fhir.jev_client.recording import JevCall
from jev_fhir.modules.bundle_router import BundleRouteResponse
from jev_fhir.modules.notifiable_detector import NotifiableDetectionResponse
from jev_fhir.modules.quality_scorer import QualityScoreResponse

DemoModule = Literal["quality", "router", "notifiable"]
Lane = Literal["auto_accepted", "routed", "flagged", "review"]


class Thresholds(BaseModel):
    quality_threshold: int = Field(ge=0, le=100)
    route_confidence_minimum: float = Field(ge=0.0, le=1.0)
    notifiable_confirmed: float = Field(ge=0.0, le=1.0)
    notifiable_review: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _review_below_confirmed(self) -> "Thresholds":
        if self.notifiable_review > self.notifiable_confirmed:
            raise ValueError("notifiable_review must be less than or equal to notifiable_confirmed")
        return self

    @classmethod
    def from_settings(cls, settings: Settings) -> "Thresholds":
        return cls(
            quality_threshold=settings.quality_threshold_default,
            route_confidence_minimum=settings.route_confidence_minimum,
            notifiable_confirmed=settings.notifiable_confidence_minimum,
            notifiable_review=settings.notifiable_review_minimum,
        )


class ThresholdOverrides(BaseModel):
    quality_threshold: int | None = Field(default=None, ge=0, le=100)
    route_confidence_minimum: float | None = Field(default=None, ge=0.0, le=1.0)
    notifiable_confirmed: float | None = Field(default=None, ge=0.0, le=1.0)
    notifiable_review: float | None = Field(default=None, ge=0.0, le=1.0)

    def apply(self, base: Thresholds) -> Thresholds:
        return Thresholds.model_validate(
            {**base.model_dump(), **self.model_dump(exclude_none=True)}
        )


class DemoConfig(BaseModel):
    mode: Literal["mock", "live"]
    jev_model: str | None
    thresholds: Thresholds
    route_options: list[str]
    questions: dict[str, str]


class FixtureEntry(BaseModel):
    id: str
    name: str
    module: DemoModule
    resource_type: str
    source: Source
    difficulty: Difficulty
    label: str
    ground_truth: dict[str, Any]
    approved: bool


class CompareRequest(BaseModel):
    resource: dict[str, Any]
    resource_type: Literal["Patient", "Observation"] | None = None
    fixture_id: str | None = None
    thresholds: ThresholdOverrides | None = None


class RuleDecision(BaseModel):
    decision: str
    score: int | None = None
    nik_valid: bool | None = None


class Verdict(BaseModel):
    jev_correct: bool | None
    rule_correct: bool | None


class CompareResponse(BaseModel):
    module: DemoModule
    jev: QualityScoreResponse | BundleRouteResponse | NotifiableDetectionResponse
    jev_decision: str
    jev_raw: list[JevCall]
    rule: RuleDecision
    ground_truth: dict[str, Any] | None
    verdict: Verdict
    serialized_state: dict[str, Any]
    override_applied: bool
    lane: Lane
    lane_reason: str
    audit_event: dict[str, Any]
    thresholds: Thresholds
    tokens_used: int
