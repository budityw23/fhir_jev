"""D1b comparer and lane-policy tests using only MockJevClient."""

import asyncio
from pathlib import Path
from typing import Literal

import pytest
from prometheus_client import REGISTRY

from jev_fhir.config import Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.compare import Comparer
from jev_fhir.demo.lanes import assign_lane
from jev_fhir.demo.schemas import CompareRequest, CompareResponse, ThresholdOverrides, Thresholds
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.modules.bundle_router import BundleRouteResponse
from jev_fhir.modules.notifiable_detector import NotifiableDetectionResponse
from jev_fhir.modules.quality_scorer import QualityScoreResponse

ROOT = Path(__file__).resolve().parents[1]


def thresholds() -> Thresholds:
    return Thresholds.from_settings(Settings())


def test_quality_lanes() -> None:
    t = thresholds()
    accepted = QualityScoreResponse(
        score=70,
        confidence=0.8,
        level="acceptable",
        missing_fields=[],
        nik_valid=True,
        nik_confidence=0.9,
        resource_reference="Patient/a",
        latency_ms=1,
        action="auto_accept",
    )
    low = accepted.model_copy(update={"score": 69, "action": "review_needed"})
    nik = accepted.model_copy(
        update={"action": "review_needed", "nik_valid": False, "nik_confidence": 0.42}
    )
    assert assign_lane("quality", accepted, t, False) == (
        "auto_accepted",
        "score 70 ≥ threshold 70",
    )
    assert assign_lane("quality", low, t, False) == ("review", "score 69 < threshold 70")
    assert assign_lane("quality", nik, t, False) == ("review", "NIK gate failed: P(valid) 0.42")


def test_router_lanes() -> None:
    t = thresholds()
    route = BundleRouteResponse(
        category="lab_result", confidence=0.8, probabilities={}, bundle_id="x", latency_ms=1
    )
    unknown = route.model_copy(update={"category": "unknown", "confidence": 0.4})
    assert assign_lane("router", route, t, False) == ("routed", "lab_result @ 0.80")
    assert assign_lane("router", unknown, t, True) == ("review", "confidence 0.40 < floor 0.50")
    assert assign_lane("router", unknown, t, False) == ("review", "model chose unknown")


def test_notifiable_lanes() -> None:
    t = thresholds()
    base = NotifiableDetectionResponse(
        is_notifiable=True,
        probability=0.8,
        status="confirmed_notifiable",
        condition_code="A90",
        condition_display="Dengue",
        flag_resource=None,
        latency_ms=1,
    )
    assert assign_lane("notifiable", base, t, False) == ("flagged", "P(notifiable) 0.80 ≥ 0.80")
    assert assign_lane(
        "notifiable",
        base.model_copy(
            update={"is_notifiable": False, "probability": 0.6, "status": "review_needed"}
        ),
        t,
        False,
    ) == ("review", "P(notifiable) 0.60 in review band")
    assert assign_lane(
        "notifiable",
        base.model_copy(
            update={"is_notifiable": False, "probability": 0.4, "status": "not_notifiable"}
        ),
        t,
        False,
    ) == ("auto_accepted", "P(notifiable) 0.40 < 0.50")


def test_concurrent_calls_are_recording_isolated_and_unknown_fixture_is_not_error() -> None:
    c = Comparer(
        MockJevClient(),
        FixtureCatalog(ROOT / "benchmarks/dataset/labels"),
        thresholds(),
        ROOT / "data/notifiable_diseases.json",
    )
    resource = FixtureCatalog(ROOT / "benchmarks/dataset/labels").load_resource(
        "tests/fixtures/patients/complete_patient.json"
    )

    async def run_both() -> tuple[CompareResponse, CompareResponse]:
        first, second = await asyncio.gather(
            c.compare("quality", CompareRequest(resource=resource)),
            c.compare("quality", CompareRequest(resource=resource, fixture_id="unknown")),
        )
        return first, second

    first, second = asyncio.run(run_both())
    # The two calls interleave (the mock awaits simulated latency). With a shared recorder one
    # result would hold all four calls and the other none; per-call recorders keep each at
    # exactly its own [score, noul] pair, with tokens that add up.
    for result in (first, second):
        assert [call.primitive for call in result.jev_raw] == ["score", "noul"]
        assert result.tokens_used == sum(call.result.tokens_used for call in result.jev_raw)
    assert second.ground_truth is None
    assert second.verdict.jev_correct is None and second.verdict.rule_correct is None


def test_router_override_and_nik_rule_gate() -> None:
    cat = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    c = Comparer(MockJevClient(), cat, thresholds(), ROOT / "data/notifiable_diseases.json")
    router = asyncio.run(
        c.compare(
            "router",
            CompareRequest(
                resource=cat.load_resource("tests/fixtures/bundles/mixed_bundle.json"),
                thresholds=ThresholdOverrides(route_confidence_minimum=0.99),
            ),
        )
    )
    patient = asyncio.run(
        c.compare(
            "quality",
            CompareRequest(resource=cat.load_resource("tests/fixtures/patients/invalid_nik.json")),
        )
    )
    assert router.override_applied and router.lane == "review"
    assert patient.rule.decision == "review_needed"


def test_known_fixture_ground_truth_verdicts_for_all_modules() -> None:
    cat = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    comparer = Comparer(MockJevClient(), cat, thresholds(), ROOT / "data/notifiable_diseases.json")
    cases: tuple[tuple[Literal["quality", "router", "notifiable"], str], ...] = (
        ("quality", "tests/fixtures/patients/complete_patient.json"),
        ("router", "tests/fixtures/bundles/lab_bundle.json"),
        ("notifiable", "tests/fixtures/conditions/dengue_a90.json"),
    )
    for module, fixture_id in cases:
        result = asyncio.run(
            comparer.compare(
                module,
                CompareRequest(resource=cat.load_resource(fixture_id), fixture_id=fixture_id),
            )
        )
        assert result.ground_truth is not None
        entry = cat.get(fixture_id)
        assert entry is not None and result.ground_truth == entry.ground_truth
        # These are easy fixtures that Jev (mock) and the rules both get right.
        assert result.verdict.jev_correct is True, fixture_id
        assert result.verdict.rule_correct is True, fixture_id


def test_non_integer_rule_score_raises_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule-score type check must survive `python -O`, so it raises rather than asserts."""
    cat = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    comparer = Comparer(MockJevClient(), cat, thresholds(), ROOT / "data/notifiable_diseases.json")
    monkeypatch.setattr(
        "jev_fhir.demo.compare.score_patient", lambda resource: {"score": None, "nik_valid": True}
    )
    resource = cat.load_resource("tests/fixtures/patients/complete_patient.json")
    with pytest.raises(TypeError, match="integer score"):
        asyncio.run(comparer.compare("quality", CompareRequest(resource=resource)))


def test_compare_records_decision_metric_for_each_module() -> None:
    """Demo compares (and so pipeline runs) must show up in jev_fhir_decisions_total."""
    cat = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    comparer = Comparer(MockJevClient(), cat, thresholds(), ROOT / "data/notifiable_diseases.json")
    cases: tuple[tuple[Literal["quality", "router", "notifiable"], str, str], ...] = (
        ("quality", "quality_scorer", "tests/fixtures/patients/complete_patient.json"),
        ("router", "bundle_router", "tests/fixtures/bundles/lab_bundle.json"),
        ("notifiable", "notifiable_detector", "tests/fixtures/conditions/dengue_a90.json"),
    )
    for module, label, fixture_id in cases:
        resource = cat.load_resource(fixture_id)
        result = asyncio.run(comparer.compare(module, CompareRequest(resource=resource)))
        labels = {"module": label, "decision": result.jev_decision}
        before = REGISTRY.get_sample_value("jev_fhir_decisions_total", labels) or 0.0
        asyncio.run(comparer.compare(module, CompareRequest(resource=resource)))
        assert REGISTRY.get_sample_value("jev_fhir_decisions_total", labels) == before + 1
