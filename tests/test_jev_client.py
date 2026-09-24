"""Unit tests for the deterministic offline Jev client."""

import json
import time
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, TypeSafeError

from jev_fhir.config import Settings
from jev_fhir.jev_client import (
    ChoiceResult,
    LiveJevClient,
    MockJevClient,
    NoulResult,
    ScoreResult,
)
from jev_fhir.jev_client.client import JevClientError
from jev_fhir.logger import configure_logging, log_decision


def test_env_example_loads_without_error() -> None:
    settings = Settings(_env_file=".env.example")  # type: ignore[call-arg]

    assert settings.mock_jev is True
    assert settings.jev_api_key


def test_decision_logger_emits_required_json_fields(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    log_decision(
        module="quality_scorer",
        resource_reference="Patient/example",
        decision="auto_accept",
        confidence=0.91,
        latency_ms=14.2,
    )

    event = json.loads(capsys.readouterr().out)
    assert event["module"] == "quality_scorer"
    assert event["resource_reference"] == "Patient/example"
    assert event["decision"] == "auto_accept"
    assert event["confidence"] == 0.91
    assert event["latency_ms"] == 14.2
    assert "timestamp" in event


@pytest.fixture
def client() -> MockJevClient:
    return MockJevClient()


@pytest.mark.asyncio
async def test_choice_returns_expected_model_shape(client: MockJevClient) -> None:
    result = await client.choice(
        {"resource_type": "Bundle", "entry_count": 3},
        "What does this bundle contain?",
        ["lab_result", "unknown"],
    )

    assert isinstance(result, ChoiceResult)
    assert result.choice in {"lab_result", "unknown"}
    assert set(result.probabilities) == {"lab_result", "unknown"}
    assert 0.6 <= result.confidence <= 0.95
    assert result.tokens_used >= 0


@pytest.mark.asyncio
async def test_score_returns_expected_model_shape(client: MockJevClient) -> None:
    result = await client.score({"resource_type": "Patient"}, "Score completeness")

    assert isinstance(result, ScoreResult)
    assert 0 <= result.score <= 100
    assert result.level_probabilities is not None
    assert 0.6 <= result.confidence <= 0.95


@pytest.mark.asyncio
async def test_noul_returns_expected_model_shape(client: MockJevClient) -> None:
    result = await client.noul({"identifier_value_length": 16}, "NIK is valid")

    assert isinstance(result, NoulResult)
    assert isinstance(result.answer, bool)
    assert 0.6 <= result.probability <= 0.95


@pytest.mark.asyncio
async def test_choice_is_deterministic(client: MockJevClient) -> None:
    state = {"resource_type": "Bundle", "entry_count": 3}
    options = ["lab_result", "unknown"]

    first = await client.choice(state, "What does this bundle contain?", options)
    second = await client.choice(state, "What does this bundle contain?", options)

    assert first.model_dump() == second.model_dump()


@pytest.mark.asyncio
async def test_mock_latency_is_simulated(client: MockJevClient) -> None:
    started_at = time.perf_counter()
    result = await client.score({"resource_type": "Patient"}, "Score completeness")
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert 10 <= result.latency_ms <= 30
    assert elapsed_ms >= 8


@pytest.mark.asyncio
async def test_choice_requires_an_option(client: MockJevClient) -> None:
    with pytest.raises(ValueError, match="at least one option"):
        await client.choice({}, "Choose", [])


def _live_client(response: Any) -> tuple[LiveJevClient, AsyncMock]:
    sdk_client = AsyncMock(spec=AsyncTypeSafeClient)
    sdk_client.system_one.return_value = response
    client = LiveJevClient(
        "test-key",
        "https://api.typesafe.ai/v1/",
        client=cast(AsyncTypeSafeClient, sdk_client),
    )
    return client, sdk_client


@pytest.mark.asyncio
async def test_live_choice_uses_sdk_typed_question() -> None:
    response = SimpleNamespace(
        choices={
            "decision": SimpleNamespace(
                choice="valid",
                probabilities={"valid": 0.9, "unknown": 0.1},
                confidence=0.8,
            )
        },
        usage=SimpleNamespace(input_tokens=12, output_tokens=3),
    )
    client, sdk_client = _live_client(response)

    result = await client.choice({"resource_type": "Patient"}, "Is it valid?", ["valid", "unknown"])

    question = sdk_client.system_one.await_args.kwargs["questions"]["decision"]
    assert isinstance(question, Choice)
    assert question.criteria == {"valid": None, "unknown": None}
    assert result.choice == "valid"
    assert result.tokens_used == 15


@pytest.mark.asyncio
async def test_live_score_maps_sdk_answer_to_requested_range() -> None:
    response = SimpleNamespace(
        scores={
            "decision": SimpleNamespace(
                score=6.3,
                probabilities={6: 0.7, 7: 0.3},
                confidence=0.7,
            )
        },
        usage=SimpleNamespace(input_tokens=20, output_tokens=4),
    )
    client, sdk_client = _live_client(response)

    result = await client.score({"resource_type": "Patient"}, "Rate completeness")

    question = sdk_client.system_one.await_args.kwargs["questions"]["decision"]
    assert isinstance(question, Score)
    assert len(question.criteria) == 10
    assert result.score == 70
    assert result.level_probabilities == {"6": 0.7, "7": 0.3}
    assert result.tokens_used == 24


@pytest.mark.asyncio
async def test_live_noul_maps_sdk_answer_to_boolean() -> None:
    response = SimpleNamespace(
        nouls={"decision": SimpleNamespace(noul=0.75)},
        usage=SimpleNamespace(input_tokens=10, output_tokens=2),
    )
    client, sdk_client = _live_client(response)

    result = await client.noul({"has_identifier": True}, "NIK is valid")

    question = sdk_client.system_one.await_args.kwargs["questions"]["decision"]
    assert isinstance(question, Noul)
    assert result.answer is True
    assert result.probability == 0.75
    assert result.tokens_used == 12


@pytest.mark.asyncio
async def test_live_client_wraps_sdk_errors() -> None:
    client, sdk_client = _live_client(None)
    sdk_error = TypeSafeError("connection failed")
    sdk_client.system_one.side_effect = sdk_error

    with pytest.raises(JevClientError, match="Jev SDK request failed") as caught:
        await client.noul({"has_identifier": True}, "NIK is valid")

    assert caught.value.__cause__ is sdk_error


def test_sdk_base_url_accepts_legacy_v1_value() -> None:
    assert LiveJevClient._sdk_base_url("https://api.typesafe.ai/v1/") == "https://api.typesafe.ai"
