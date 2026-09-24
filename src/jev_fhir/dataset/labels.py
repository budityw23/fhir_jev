"""Validated dataset labels used by benchmarks and the demo catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, Field, model_validator

from jev_fhir.config import PROJECT_ROOT

Source = Literal["unit", "hard", "generated", "demo"]
Difficulty = Literal["easy", "hard"]
L = TypeVar("L", bound="LabelBase")
QUALITY_LABEL_THRESHOLD = 70


class LabelBase(BaseModel):
    """Common provenance for a manually reviewed fixture label."""

    fixture: str
    source: Source
    difficulty: Difficulty
    rationale: str = Field(min_length=10)
    approved_by: str | None = None


class QualityLabel(LabelBase):
    """A human-authored quality expectation at the standard threshold of 70."""

    resource_type: Literal["Patient", "Observation"]
    expected_action: Literal["auto_accept", "review_needed"]
    expected_score_range: tuple[int, int]
    expected_nik_valid: bool | None = None

    @model_validator(mode="after")
    def _banded(self) -> QualityLabel:
        lower, upper = self.expected_score_range
        if not 0 <= lower < upper <= 100 or upper - lower < 20:
            raise ValueError("expected_score_range must be a 0–100 band at least 20 points wide")
        return self

    @model_validator(mode="after")
    def _action_consistent(self) -> QualityLabel:
        """Keep the action, score band and NIK gate telling the same story at threshold 70."""
        lower, upper = self.expected_score_range
        if self.expected_action == "auto_accept":
            if lower < QUALITY_LABEL_THRESHOLD:
                raise ValueError("auto_accept requires a score band entirely >= 70")
            if self.expected_nik_valid is False:
                raise ValueError("auto_accept is impossible when the NIK gate fails")
        elif upper >= QUALITY_LABEL_THRESHOLD and self.expected_nik_valid is not False:
            raise ValueError("review_needed with a passing NIK requires a score band entirely < 70")
        return self


class RouteLabel(LabelBase):
    """Expected category for a FHIR Bundle routing decision."""

    expected_category: Literal[
        "lab_result", "medication_dispense", "immunization_report", "encounter_summary", "unknown"
    ]


class NotifiableLabel(LabelBase):
    """Expected reporting status for a FHIR Condition."""

    expected_status: Literal["confirmed_notifiable", "review_needed", "not_notifiable"]

    @property
    def expected_notifiable(self) -> bool:
        """Return the binary form consumed by the detector benchmark."""
        return self.expected_status == "confirmed_notifiable"


def load_labels(path: Path, model: type[L]) -> list[L]:
    """Load and validate a JSON array of labels."""
    return [model.model_validate(item) for item in json.loads(path.read_text())]


def fixture_path(label: LabelBase) -> Path:
    """Resolve a root-relative fixture path without allowing traversal."""
    candidate = (PROJECT_ROOT / label.fixture).resolve()
    if PROJECT_ROOT not in candidate.parents:
        raise ValueError("fixture path must stay inside the project root")
    return candidate
