"""Async Jev protocol and TypeSafe SDK implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any, ClassVar

from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    Noul,
    RetryPolicy,
    Score,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
)

from jev_fhir.jev_client.models import ChoiceResult, NoulResult, ScoreResult


class JevClientError(RuntimeError):
    """Base Jev error, mapped to a 502 ``jev_error`` API response."""

    error_code: ClassVar[str] = "jev_error"
    status_code: ClassVar[int] = 502


class JevTimeoutError(JevClientError):
    """The TypeSafe SDK exhausted its request timeout budget."""

    error_code = "jev_timeout"
    status_code = 504


class JevRateLimitError(JevClientError):
    """The TypeSafe service rate-limited the request."""

    error_code = "jev_rate_limited"
    status_code = 429


class JevAuthError(JevClientError):
    """The TypeSafe API key was rejected or lacks permission."""

    error_code = "jev_auth"
    status_code = 502


class JevClient(ABC):
    """Interface shared by production and offline Jev clients."""

    @abstractmethod
    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        """Choose one declared option for a structured state."""

    @abstractmethod
    async def score(
        self, state: dict[str, Any], question: str, scale_min: int = 0, scale_max: int = 100
    ) -> ScoreResult:
        """Score a structured state on a bounded integer scale."""

    @abstractmethod
    async def noul(self, state: dict[str, Any], statement: str) -> NoulResult:
        """Evaluate a boolean statement against a structured state."""


class LiveJevClient(JevClient):
    """Jev adapter backed by TypeSafe's supported asynchronous Python SDK."""

    _QUALITY_LEVELS = [
        "0: empty, invalid, or unusable clinical resource",
        "11: almost entirely incomplete or malformed",
        "22: severely incomplete, with only minimal usable information",
        "33: incomplete, with major fields missing or malformed",
        "44: partially complete but requires substantial review",
        "56: usable but has notable missing or questionable fields",
        "67: mostly complete with some fields requiring review",
        "78: complete enough for routine use with minor gaps",
        "89: highly complete and well-formed with negligible gaps",
        "100: fully complete, correctly formatted, and clinically complete",
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        model: str = "jev-latest",
        timeout_s: float = 5.0,
        max_retries: int = 2,
        retry_budget_s: float = 12.0,
        client: AsyncTypeSafeClient | None = None,
    ) -> None:
        self.model = model
        self._owns_client = client is None
        self._client = client or AsyncTypeSafeClient(
            api_key=api_key,
            base_url=self._sdk_base_url(base_url),
            model=model,
            timeout=timeout_s,
            retry=RetryPolicy(max_retries=max_retries, timeout=retry_budget_s),
        )

    async def __aenter__(self) -> LiveJevClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the internally-created SDK client."""
        if self._owns_client:
            await self._client.aclose()

    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        if not options:
            raise ValueError("choice requires at least one option")
        response, latency_ms = await self._system_one(
            state,
            {
                "decision": Choice(
                    instructions=question, criteria={option: None for option in options}
                )
            },
        )
        answer = response.choices["decision"]
        return ChoiceResult(
            choice=answer.choice,
            confidence=answer.confidence,
            probabilities=answer.probabilities,
            latency_ms=latency_ms,
            tokens_used=self._tokens_used(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )

    async def score(
        self, state: dict[str, Any], question: str, scale_min: int = 0, scale_max: int = 100
    ) -> ScoreResult:
        if scale_min > scale_max:
            raise ValueError("scale_min cannot exceed scale_max")
        response, latency_ms = await self._system_one(
            state, {"decision": Score(instructions=question, criteria=self._QUALITY_LEVELS)}
        )
        answer = response.scores["decision"]
        score = round(
            scale_min + (answer.score / (len(self._QUALITY_LEVELS) - 1)) * (scale_max - scale_min)
        )
        return ScoreResult(
            score=score,
            confidence=answer.confidence,
            level_probabilities={
                str(level): probability for level, probability in answer.probabilities.items()
            },
            latency_ms=latency_ms,
            tokens_used=self._tokens_used(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )

    async def noul(self, state: dict[str, Any], statement: str) -> NoulResult:
        response, latency_ms = await self._system_one(
            state, {"decision": Noul(instructions=statement)}
        )
        answer = response.nouls["decision"]
        return NoulResult(
            answer=answer.noul >= 0.5,
            probability=answer.noul,
            latency_ms=latency_ms,
            tokens_used=self._tokens_used(
                response.usage.input_tokens, response.usage.output_tokens
            ),
        )

    async def _system_one(
        self, state: dict[str, Any], questions: dict[str, Any]
    ) -> tuple[Any, float]:
        started_at = perf_counter()
        try:
            response = await self._client.system_one(state=state, questions=questions)
        except TypeSafeAPITimeoutError as error:
            raise JevTimeoutError(self._message(error)) from error
        except TypeSafeRateLimitError as error:
            raise JevRateLimitError(self._message(error)) from error
        except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError) as error:
            raise JevAuthError(self._message(error)) from error
        except TypeSafeAPIConnectionError as error:
            raise JevClientError(self._message(error)) from error
        except TypeSafeError as error:
            raise JevClientError(self._message(error)) from error
        return response, (perf_counter() - started_at) * 1000

    @staticmethod
    def _message(error: TypeSafeError) -> str:
        return f"Jev SDK request failed: {type(error).__name__}"

    @staticmethod
    def _tokens_used(input_tokens: int | None, output_tokens: int | None) -> int:
        return (input_tokens or 0) + (output_tokens or 0)

    @staticmethod
    def _sdk_base_url(base_url: str) -> str:
        """Accept a legacy ``.../v1/`` value while configuring the SDK root."""
        return base_url.rstrip("/").removesuffix("/v1")
