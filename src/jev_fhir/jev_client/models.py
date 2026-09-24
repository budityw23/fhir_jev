"""Typed results returned by Jev decision primitives."""

from pydantic import BaseModel, Field


class ChoiceResult(BaseModel):
    """Result of a Jev Choice decision."""

    choice: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]
    latency_ms: float = Field(ge=0.0)
    tokens_used: int = Field(ge=0)


class ScoreResult(BaseModel):
    """Result of a Jev Score decision."""

    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    level_probabilities: dict[str, float] | None = None
    latency_ms: float = Field(ge=0.0)
    tokens_used: int = Field(ge=0)


class NoulResult(BaseModel):
    """Result of a Jev Noul (boolean) decision."""

    answer: bool
    probability: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    tokens_used: int = Field(ge=0)
