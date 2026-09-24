"""Tests for Phase 3 decision modules and FHIR helper builders."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fhir.resources.R4B.auditevent import AuditEvent
from fhir.resources.R4B.flag import Flag
from pydantic import ValidationError
from pydantic.v1 import ValidationError as PydanticV1ValidationError

from jev_fhir.fhir_helpers.audit_event import AuditEventBuilder
from jev_fhir.jev_client.client import JevClient
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.jev_client.models import ChoiceResult, NoulResult, ScoreResult
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES / relative_path).read_text()))


class StubJevClient(JevClient):
    """Small deterministic Jev double with call recording."""

    def __init__(
        self,
        *,
        score_result: ScoreResult | None = None,
        choice_result: ChoiceResult | None = None,
        noul_result: NoulResult | None = None,
    ) -> None:
        self.score_result = score_result or ScoreResult(
            score=80, confidence=0.9, latency_ms=12, tokens_used=10
        )
        self.choice_result = choice_result or ChoiceResult(
            choice="lab_result",
            confidence=0.9,
            probabilities={"lab_result": 0.9, "unknown": 0.1},
            latency_ms=12,
            tokens_used=10,
        )
        self.noul_result = noul_result or NoulResult(
            answer=True, probability=0.95, latency_ms=12, tokens_used=10
        )
        self.calls: list[str] = []

    async def choice(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> ChoiceResult:
        self.calls.append("choice")
        return self.choice_result

    async def score(
        self,
        state: dict[str, Any],
        question: str,
        scale_min: int = 0,
        scale_max: int = 100,
    ) -> ScoreResult:
        self.calls.append("score")
        return self.score_result

    async def noul(self, state: dict[str, Any], statement: str) -> NoulResult:
        self.calls.append("noul")
        return self.noul_result


@pytest.mark.asyncio
async def test_quality_scorer_returns_patient_response_shape() -> None:
    client = StubJevClient()
    response = await QualityScorer(client).score(
        load_fixture("patients/complete_patient.json"), "Patient"
    )

    assert response.score == 80
    assert response.action == "auto_accept"
    assert response.nik_valid is True
    assert response.resource_reference == "Patient/12345"
    assert client.calls == ["score", "noul"]


@pytest.mark.asyncio
async def test_quality_scorer_nik_gate_blocks_auto_accept_despite_high_score() -> None:
    client = StubJevClient(
        score_result=ScoreResult(score=95, confidence=0.9, latency_ms=12, tokens_used=10),
        noul_result=NoulResult(answer=False, probability=0.08, latency_ms=12, tokens_used=10),
    )
    response = await QualityScorer(client).score(
        load_fixture("patients/invalid_nik.json"), "Patient", threshold=70
    )

    assert response.score == 95
    assert response.nik_valid is False
    assert response.action == "review_needed"
    assert response.level == "review_needed"


@pytest.mark.asyncio
async def test_quality_scorer_nik_gate_with_mock_client_on_invalid_nik_fixture() -> None:
    response = await QualityScorer(MockJevClient()).score(
        load_fixture("patients/invalid_nik.json"), "Patient"
    )

    assert response.score >= 70
    assert response.nik_valid is False
    assert response.action == "review_needed"


@pytest.mark.asyncio
async def test_quality_scorer_skips_noul_for_observation() -> None:
    client = StubJevClient(
        score_result=ScoreResult(score=20, confidence=0.8, latency_ms=12, tokens_used=10)
    )
    observation = load_fixture("bundles/lab_bundle.json")["entry"][0]["resource"]
    response = await QualityScorer(client).score(observation, "Observation", threshold=70)

    assert response.action == "review_needed"
    assert response.nik_valid is None
    assert response.nik_confidence is None
    assert client.calls == ["score"]


@pytest.mark.asyncio
async def test_quality_scorer_rejects_mismatched_resource_type() -> None:
    with pytest.raises(ValueError, match="does not match"):
        await QualityScorer(StubJevClient()).score(
            load_fixture("patients/complete_patient.json"), "Observation"
        )


@pytest.mark.asyncio
async def test_bundle_router_returns_high_confidence_choice() -> None:
    response = await BundleRouter(StubJevClient()).route(load_fixture("bundles/lab_bundle.json"))

    assert response.category == "lab_result"
    assert response.bundle_id == "lab-bundle"


@pytest.mark.asyncio
async def test_bundle_router_overrides_low_confidence_choice() -> None:
    client = StubJevClient(
        choice_result=ChoiceResult(
            choice="lab_result",
            confidence=0.49,
            probabilities={"lab_result": 0.49, "unknown": 0.51},
            latency_ms=12,
            tokens_used=10,
        )
    )
    response = await BundleRouter(client).route(load_fixture("bundles/lab_bundle.json"))

    assert response.category == "unknown"


@pytest.mark.asyncio
async def test_bundle_router_rejects_invalid_bundle() -> None:
    with pytest.raises((ValidationError, PydanticV1ValidationError)):
        await BundleRouter(StubJevClient()).route({"resourceType": "Patient"})


@pytest.mark.asyncio
async def test_notifiable_detector_confirms_dengue_and_builds_flag() -> None:
    response = await NotifiableDiseaseDetector(StubJevClient()).detect(
        load_fixture("conditions/dengue_a90.json")
    )

    assert response.is_notifiable is True
    assert response.status == "confirmed_notifiable"
    assert response.condition_code == "A90"
    assert response.flag_resource is not None
    Flag.parse_obj(response.flag_resource)


@pytest.mark.asyncio
async def test_notifiable_detector_rejects_common_cold() -> None:
    client = StubJevClient(
        noul_result=NoulResult(answer=False, probability=0.1, latency_ms=12, tokens_used=10)
    )
    response = await NotifiableDiseaseDetector(client).detect(
        load_fixture("conditions/common_cold_j06.json")
    )

    assert response.is_notifiable is False
    assert response.status == "not_notifiable"
    assert response.flag_resource is None


@pytest.mark.asyncio
async def test_notifiable_detector_marks_mid_confidence_for_review() -> None:
    client = StubJevClient(
        noul_result=NoulResult(answer=True, probability=0.6, latency_ms=12, tokens_used=10)
    )
    response = await NotifiableDiseaseDetector(client).detect(
        load_fixture("conditions/dengue_a90.json")
    )

    assert response.is_notifiable is False
    assert response.status == "review_needed"


@pytest.mark.asyncio
async def test_phase_three_modules_work_with_mock_jev_client() -> None:
    client = MockJevClient()
    quality = await QualityScorer(client).score(
        load_fixture("patients/complete_patient.json"), "Patient"
    )
    route = await BundleRouter(client).route(load_fixture("bundles/lab_bundle.json"))
    dengue = await NotifiableDiseaseDetector(client).detect(
        load_fixture("conditions/dengue_a90.json")
    )
    cold = await NotifiableDiseaseDetector(client).detect(
        load_fixture("conditions/common_cold_j06.json")
    )

    assert quality.action == "auto_accept"
    assert quality.nik_valid is True
    assert route.category == "lab_result"
    assert dengue.status == "confirmed_notifiable"
    assert cold.status == "not_notifiable"


def test_audit_event_builder_returns_valid_fhir_resource() -> None:
    event = AuditEventBuilder().build(
        module_name="quality_scorer",
        decision="auto_accept",
        resource_reference="Patient/12345",
        timestamp=datetime(2026, 9, 23, tzinfo=UTC),
    )

    AuditEvent.parse_obj(event)
    assert "Patient/12345" in json.dumps(event)
    # R4 shape: `type` is a Coding and entity.detail.type is a string (R5 uses `code` and a
    # CodeableConcept, which R4 servers reject).
    assert "code" not in event
    assert event["type"] == {
        "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
        "code": "rest",
        "display": "RESTful Operation",
    }
    assert event["entity"] == [
        {
            "what": {"reference": "Patient/12345"},
            "detail": [{"type": "decision", "valueString": "auto_accept"}],
        }
    ]
