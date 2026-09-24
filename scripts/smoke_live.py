"""Run one authenticated live Jev decision through each demo module."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, cast

from jev_fhir.config import PROJECT_ROOT, Settings
from jev_fhir.jev_client import JevClientError, LiveJevClient, RecordingJevClient
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer


def load_fixture(relative_path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((PROJECT_ROOT / relative_path).read_text()))


async def run() -> int:
    settings = Settings()
    if settings.jev_api_key in {"mock-key", "your-key-here"}:
        print(
            "Live smoke requires a real JEV_API_KEY in .env; no network call was made.",
            file=sys.stderr,
        )
        return 2
    client = LiveJevClient(
        settings.jev_api_key,
        settings.jev_base_url,
        model=settings.jev_model,
        timeout_s=settings.jev_timeout_s,
        max_retries=settings.jev_max_retries,
        retry_budget_s=settings.jev_retry_budget_s,
    )
    try:
        for name, module, resource, resource_type in [
            (
                "quality",
                QualityScorer,
                load_fixture("tests/fixtures/patients/complete_patient.json"),
                "Patient",
            ),
            ("router", BundleRouter, load_fixture("tests/fixtures/bundles/lab_bundle.json"), None),
            (
                "notifiable",
                NotifiableDiseaseDetector,
                load_fixture("tests/fixtures/conditions/japanese_encephalitis_a83.json"),
                None,
            ),
        ]:
            recording = RecordingJevClient(client)
            try:
                if name == "quality":
                    result = await module(recording).score(resource, cast(str, resource_type))
                    decision, confidence = result.action, result.confidence
                elif name == "router":
                    result = await module(recording).route(resource)
                    decision, confidence = result.category, result.confidence
                else:
                    result = await module(recording).detect(resource)
                    decision, confidence = result.status, result.probability
            except JevClientError as error:
                print(f"{name}: {error.error_code}", file=sys.stderr)
                return 1
            latency_ms = sum(call.result.latency_ms for call in recording.calls)
            print(
                f"{name:12} {decision:24} confidence={confidence:.3f} "
                f"latency_ms={latency_ms:.1f} tokens={recording.total_tokens}"
            )
    finally:
        await client.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
