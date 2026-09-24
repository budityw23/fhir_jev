"""A per-request Jev client decorator that retains raw primitive results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from jev_fhir.jev_client.client import JevClient
from jev_fhir.jev_client.models import ChoiceResult, NoulResult, ScoreResult


class JevCall(BaseModel):
    """One typed Jev primitive call and its raw result."""

    primitive: Literal["choice", "score", "noul"]
    question: str
    options: list[str] | None = None
    result: ChoiceResult | ScoreResult | NoulResult


class RecordingJevClient(JevClient):
    """Forward calls to an inner client and retain results for one operation."""

    def __init__(self, inner: JevClient) -> None:
        self._inner = inner
        self._calls: list[JevCall] = []

    @property
    def calls(self) -> list[JevCall]:
        """Return a copy of the calls recorded so far."""
        return self._calls.copy()

    @property
    def total_tokens(self) -> int:
        """Return the total tokens across calls recorded so far."""
        return sum(call.result.tokens_used for call in self._calls)

    def drain(self) -> list[JevCall]:
        """Return recorded calls and clear the buffer."""
        calls = self.calls
        self._calls.clear()
        return calls

    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        result = await self._inner.choice(state, question, options)
        self._calls.append(
            JevCall(primitive="choice", question=question, options=options, result=result)
        )
        return result

    async def score(
        self, state: dict[str, Any], question: str, scale_min: int = 0, scale_max: int = 100
    ) -> ScoreResult:
        result = await self._inner.score(state, question, scale_min, scale_max)
        self._calls.append(JevCall(primitive="score", question=question, result=result))
        return result

    async def noul(self, state: dict[str, Any], statement: str) -> NoulResult:
        result = await self._inner.noul(state, statement)
        self._calls.append(JevCall(primitive="noul", question=statement, result=result))
        return result
