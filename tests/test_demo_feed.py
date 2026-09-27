"""D1c DecisionFeed contract tests."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from jev_fhir.config import Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.compare import Comparer
from jev_fhir.demo.feed import DecisionEvent, DecisionFeed, RunEvent, event_from_compare
from jev_fhir.demo.schemas import CompareRequest, DemoModule, Thresholds
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.modules.bundle_router import BundleRouteResponse
from jev_fhir.modules.notifiable_detector import NotifiableDetectionResponse
from jev_fhir.modules.quality_scorer import QualityScoreResponse

ROOT = Path(__file__).resolve().parents[1]


def decision(index: int = 0) -> DecisionEvent:
    return DecisionEvent(
        seq=0,
        timestamp=datetime.now(UTC),
        run_id=None,
        fixture_id=None,
        module="quality",
        resource_reference=f"Patient/{index}",
        decision="auto_accept",
        confidence=0.9,
        lane="auto_accepted",
        lane_reason="ok",
        latency_ms=1,
        jev_latency_ms=1,
        tokens_used=1,
        ground_truth_match=True,
    )


def comparer() -> tuple[Comparer, FixtureCatalog]:
    catalog = FixtureCatalog(ROOT / "benchmarks/dataset/labels")
    return (
        Comparer(
            MockJevClient(),
            catalog,
            Thresholds.from_settings(Settings()),
            ROOT / "data/notifiable_diseases.json",
        ),
        catalog,
    )


def test_feed_maxlen_recent_since_and_sequence() -> None:
    feed = DecisionFeed(maxlen=2)
    assert feed.publish(decision(1)) == 1
    assert feed.publish(RunEvent(run_id="r", status="started", total=1, processed=0)) == 2
    assert feed.publish(decision(3)) == 3
    assert [event.seq for event in feed.recent()] == [3]
    assert [seq for seq, _ in feed.since(1)] == [2, 3]


@pytest.mark.asyncio
async def test_slow_subscriber_overflow_drops_only_its_oldest_item() -> None:
    feed = DecisionFeed()
    async with feed.subscribe() as slow, feed.subscribe() as fast:
        for index in range(1002):
            feed.publish(decision(index))
        assert (await anext(slow))[0] == 3
        assert (await anext(fast))[0] == 3
        assert feed.subscriber_count == 2


@pytest.mark.asyncio
async def test_subscription_unregisters_normally_and_after_break() -> None:
    feed = DecisionFeed()
    async with feed.subscribe() as sub:
        assert feed.subscriber_count == 1
        feed.publish(decision())
        async for _ in sub:
            break
    assert feed.subscriber_count == 0


@pytest.mark.asyncio
async def test_subscription_unregisters_when_consumer_is_cancelled() -> None:
    feed = DecisionFeed()

    async def consume() -> None:
        async with feed.subscribe() as sub:
            await anext(sub)

    task = asyncio.create_task(consume())
    for _ in range(20):
        if feed.subscriber_count:
            break
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert feed.subscriber_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "fixture_id"),
    [
        ("quality", "tests/fixtures/patients/complete_patient.json"),
        ("router", "tests/fixtures/bundles/mixed_bundle.json"),
        ("notifiable", "tests/fixtures/conditions/japanese_encephalitis_a83.json"),
    ],
)
async def test_event_from_compare_maps_every_contract_field(
    module: DemoModule, fixture_id: str
) -> None:
    compare_service, catalog = comparer()
    response = await compare_service.compare(
        module, CompareRequest(resource=catalog.load_resource(fixture_id), fixture_id=fixture_id)
    )
    event = event_from_compare(response, run_id="run-1", fixture_id=fixture_id)
    assert event.seq == 0
    assert event.run_id == "run-1" and event.fixture_id == fixture_id
    assert event.resource_reference == response.audit_event["entity"][0]["what"]["reference"]
    assert event.decision == response.jev_decision
    if module == "notifiable":
        expected_confidence = cast(NotifiableDetectionResponse, response.jev).probability
    else:
        expected_confidence = cast(
            QualityScoreResponse | BundleRouteResponse, response.jev
        ).confidence
    assert event.confidence == expected_confidence
    assert event.lane == response.lane and event.lane_reason == response.lane_reason
    assert event.latency_ms == response.jev.latency_ms
    assert event.jev_latency_ms == sum(call.result.latency_ms for call in response.jev_raw)
    assert event.tokens_used == response.tokens_used
    assert event.ground_truth_match == response.verdict.jev_correct
    assert event.error is None
