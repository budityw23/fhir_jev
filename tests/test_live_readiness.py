"""D0 live-readiness regression tests; all SDK calls are mocked."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx2 import Headers
from typesafe_sdk import (
    AsyncTypeSafeClient,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeRateLimitError,
)

from jev_fhir.config import Settings
from jev_fhir.dataset.labels import QualityLabel
from jev_fhir.jev_client import (
    JevAuthError,
    JevClientError,
    JevRateLimitError,
    JevTimeoutError,
    LiveJevClient,
    MockJevClient,
    RecordingJevClient,
)
from jev_fhir.main import create_app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sdk_error", "expected_error"),
    [
        (TypeSafeAPITimeoutError(1.0), JevTimeoutError),
        (TypeSafeRateLimitError(429, {}, Headers()), JevRateLimitError),
        (TypeSafeAuthenticationError(401, {}, Headers()), JevAuthError),
        (TypeSafeAPIConnectionError("offline"), JevClientError),
    ],
)
async def test_live_client_maps_sdk_errors(
    sdk_error: Exception, expected_error: type[JevClientError]
) -> None:
    sdk_client = AsyncMock(spec=AsyncTypeSafeClient)
    sdk_client.system_one.side_effect = sdk_error
    client = LiveJevClient(
        "test-key", "https://api.typesafe.ai", client=cast(AsyncTypeSafeClient, sdk_client)
    )

    with pytest.raises(expected_error) as caught:
        await client.noul({}, "A statement")

    assert caught.value.__cause__ is sdk_error
    assert type(sdk_error).__name__ in str(caught.value)


def test_live_client_passes_configured_sdk_options() -> None:
    with patch("jev_fhir.jev_client.client.AsyncTypeSafeClient") as sdk_client:
        LiveJevClient(
            "test-key",
            "https://api.typesafe.ai/v1/",
            model="jev-1.13.0",
            timeout_s=4.0,
            max_retries=3,
            retry_budget_s=11.0,
        )

    kwargs = sdk_client.call_args.kwargs
    retry = cast(RetryPolicy, kwargs["retry"])
    assert kwargs["base_url"] == "https://api.typesafe.ai"
    assert kwargs["model"] == "jev-1.13.0"
    assert kwargs["timeout"] == 4.0
    assert retry.max_retries == 3
    assert retry.timeout == 11.0


@pytest.mark.asyncio
async def test_recording_client_captures_calls_tokens_and_drain() -> None:
    client = RecordingJevClient(MockJevClient())
    await client.choice({"contains_lab_codes": True}, "Route", ["lab_result", "unknown"])
    await client.score({"field_completeness": 8, "field_total": 10}, "Quality")
    await client.noul({"identifier_value_length": 16}, "16-digit Indonesian NIK")

    assert [call.primitive for call in client.calls] == ["choice", "score", "noul"]
    assert client.total_tokens == sum(call.result.tokens_used for call in client.calls)
    assert len(client.drain()) == 3
    assert client.calls == []


@pytest.mark.asyncio
async def test_mock_nik_probability_is_probability_true() -> None:
    client = MockJevClient()
    valid = await client.noul({"identifier_value_length": 16}, "16-digit Indonesian NIK")
    invalid = await client.noul({"identifier_value_length": 15}, "16-digit Indonesian NIK")

    assert valid.answer is True and valid.probability > 0.5
    assert invalid.answer is False and invalid.probability < 0.5


@pytest.mark.parametrize("score_range", [(70, 70), (60, 75), (-1, 30), (20, 101)])
def test_quality_label_rejects_non_banded_ranges(score_range: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        QualityLabel(
            fixture="tests/fixtures/patients/complete_patient.json",
            source="unit",
            difficulty="easy",
            rationale="This deliberately tests invalid label bands.",
            resource_type="Patient",
            expected_action="auto_accept",
            expected_score_range=score_range,
        )


def test_health_includes_model_and_route_defaults_use_settings() -> None:
    app = create_app(Settings(mock_jev=True, quality_threshold_default=90))
    with TestClient(app) as client:
        health = client.get("/health")
        response = client.post(
            "/api/v1/quality-score",
            json={
                "resource_type": "Patient",
                "resource": __import__("json").loads(
                    Path("tests/fixtures/patients/complete_patient.json").read_text()
                ),
            },
        )

    assert health.json()["jev_model"] is None
    assert response.status_code == 200
    assert response.json()["action"] == "review_needed"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (JevTimeoutError("timeout"), 504, "jev_timeout"),
        (JevRateLimitError("limited"), 429, "jev_rate_limited"),
        (JevAuthError("auth"), 502, "jev_auth"),
        (JevClientError("other"), 502, "jev_error"),
    ],
)
def test_api_maps_typed_jev_errors(error: JevClientError, status: int, code: str) -> None:
    app = create_app(Settings(mock_jev=True))

    @app.get("/_test_jev_error")
    async def raise_error() -> None:
        raise error

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test_jev_error")

    assert response.status_code == status
    assert response.json()["error"] == code
