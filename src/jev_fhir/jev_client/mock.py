"""Deterministic offline Jev implementation used by tests and local development."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from jev_fhir.jev_client.client import JevClient
from jev_fhir.jev_client.models import ChoiceResult, NoulResult, ScoreResult


class MockJevClient(JevClient):
    """Return stable, plausible decisions without making network calls."""

    @staticmethod
    def _digest(*parts: object) -> bytes:
        encoded = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).digest()

    @classmethod
    async def _simulate_latency(cls, *parts: object) -> float:
        latency_ms = 10 + (cls._digest(*parts)[0] % 21)
        await asyncio.sleep(latency_ms / 1000)
        return float(latency_ms)

    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        if not options:
            raise ValueError("choice requires at least one option")
        latency_ms = await self._simulate_latency("choice", state, question, options)
        digest = self._digest("choice", state, question, options)
        if state.get("contains_lab_codes") is True and "lab_result" in options:
            choice, confidence = "lab_result", 0.92
        elif state.get("contains_immunization") is True and "immunization_report" in options:
            choice, confidence = "immunization_report", 0.92
        elif state.get("contains_medication") is True and "medication_dispense" in options:
            choice, confidence = "medication_dispense", 0.92
        elif state.get("has_encounter_reference") is True and "encounter_summary" in options:
            choice, confidence = "encounter_summary", 0.92
        else:
            choice = options[digest[0] % len(options)]
            confidence = round(0.60 + ((digest[1] % 36) / 100), 2)
        residual = (1 - confidence) / max(len(options) - 1, 1)
        probabilities = {option: round(residual, 4) for option in options}
        probabilities[choice] = confidence
        return ChoiceResult(
            choice=choice,
            confidence=confidence,
            probabilities=probabilities,
            latency_ms=latency_ms,
            tokens_used=10 + (digest[2] % 31),
        )

    async def score(
        self,
        state: dict[str, Any],
        question: str,
        scale_min: int = 0,
        scale_max: int = 100,
    ) -> ScoreResult:
        if scale_min > scale_max:
            raise ValueError("scale_min cannot exceed scale_max")
        latency_ms = await self._simulate_latency("score", state, question, scale_min, scale_max)
        digest = self._digest("score", state, question, scale_min, scale_max)
        completeness = state.get("field_completeness")
        total = state.get("field_total")
        if isinstance(completeness, int) and isinstance(total, int) and total > 0:
            score = scale_min + round((scale_max - scale_min) * completeness / total)
        else:
            score = scale_min + (digest[0] % (scale_max - scale_min + 1))
        confidence = round(0.60 + ((digest[1] % 36) / 100), 2)
        return ScoreResult(
            score=score,
            confidence=confidence,
            level_probabilities={"low": round(1 - confidence, 2), "high": confidence},
            latency_ms=latency_ms,
            tokens_used=10 + (digest[2] % 31),
        )

    async def noul(self, state: dict[str, Any], statement: str) -> NoulResult:
        latency_ms = await self._simulate_latency("noul", state, statement)
        digest = self._digest("noul", state, statement)
        if "16-digit Indonesian NIK" in statement:
            answer = state.get("identifier_value_length") == 16
            probability = 0.94 if answer else 0.08
        elif "notifiable disease" in statement.lower():
            code = state.get("code_value")
            notifiable_codes = {
                "A00",
                "A01",
                "A15",
                "A16",
                "A17",
                "A18",
                "A19",
                "A30",
                "A83.0",
                "A90",
                "A91",
                "B20",
                "B50",
                "B51",
                "B52",
                "B53",
                "B54",
            }
            answer = isinstance(code, str) and code in notifiable_codes
            probability = 0.95 if answer else 0.1
        else:
            answer = bool(digest[0] % 2)
            probability = round(0.60 + ((digest[1] % 36) / 100), 2)
        return NoulResult(
            answer=answer,
            probability=probability,
            latency_ms=latency_ms,
            tokens_used=10 + (digest[2] % 31),
        )
