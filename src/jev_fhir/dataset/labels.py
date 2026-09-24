"""Validated dataset labels used by benchmarks and the demo catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, Field, model_validator

from jev_fhir.config import PROJECT_ROOT

Source = Literal["unit", "hard", "generated", "demo"]
Difficulty = Literal["easy", "hard"]
L = TypeVar("L", bound="LabelBase")


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


def load_labels(path: Path, model: type[L]) -> list[L]:
    """Load and validate a JSON array of labels."""
    return [model.model_validate(item) for item in __import__("json").loads(path.read_text())]


def fixture_path(label: LabelBase) -> Path:
    """Resolve a root-relative fixture path without allowing traversal."""
    candidate = (PROJECT_ROOT / label.fixture).resolve()
    if PROJECT_ROOT not in candidate.parents:
        raise ValueError("fixture path must stay inside the project root")
    return candidate
