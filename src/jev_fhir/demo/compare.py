"""Per-request Jev and rule-baseline comparison for the demo API."""

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from jev_fhir.baselines.bundle_router import route_bundle
from jev_fhir.baselines.notifiable import is_notifiable
from jev_fhir.baselines.quality import score_observation, score_patient
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.demo.lanes import assign_lane
from jev_fhir.demo.schemas import (
    CompareRequest,
    CompareResponse,
    DemoModule,
    RuleDecision,
    Thresholds,
    Verdict,
)
from jev_fhir.fhir_helpers.audit_event import AuditEventBuilder
from jev_fhir.jev_client.client import JevClient
from jev_fhir.jev_client.recording import RecordingJevClient
from jev_fhir.metrics import record_decision
from jev_fhir.modules.bundle_router import BundleRouter, BundleRouteResponse
from jev_fhir.modules.notifiable_detector import (
    NotifiableDetectionResponse,
    NotifiableDiseaseDetector,
)
from jev_fhir.modules.quality_scorer import QualityScorer, QualityScoreResponse
from jev_fhir.serializer.bundle import BundleSerializer
from jev_fhir.serializer.condition import ConditionSerializer
from jev_fhir.serializer.observation import ObservationSerializer
from jev_fhir.serializer.patient import PatientSerializer


class Comparer:
    """Compare fresh Jev module executions with transparent rule baselines."""

    def __init__(
        self,
        jev_client: JevClient,
        catalog: FixtureCatalog,
        base_thresholds: Thresholds,
        disease_data_path: Path,
    ) -> None:
        self._jev_client = jev_client
        self._catalog = catalog
        self._base_thresholds = base_thresholds
        self._disease_data_path = disease_data_path

    async def compare(self, module: DemoModule, request: CompareRequest) -> CompareResponse:
        thresholds = (
            request.thresholds.apply(self._base_thresholds)
            if request.thresholds
            else self._base_thresholds
        )
        recording = RecordingJevClient(self._jev_client)
        resource = request.resource
        override = False
        response: QualityScoreResponse | BundleRouteResponse | NotifiableDetectionResponse
        if module == "quality":
            resource_type = request.resource_type or cast(str, resource.get("resourceType"))
            response = await QualityScorer(recording).score(
                resource, resource_type, thresholds.quality_threshold
            )
            baseline = (
                score_patient(resource)
                if resource_type == "Patient"
                else score_observation(resource)
            )
            score = baseline["score"]
            if not isinstance(score, int):
                raise TypeError("rule quality baseline must return an integer score")
            rule = RuleDecision(
                decision="auto_accept"
                if score >= thresholds.quality_threshold and baseline["nik_valid"] is not False
                else "review_needed",
                score=score,
                nik_valid=cast(bool | None, baseline["nik_valid"]),
            )
            state = (
                PatientSerializer() if resource_type == "Patient" else ObservationSerializer()
            ).serialize(resource)
            decision = response.action
            confidence = response.confidence
            reference = response.resource_reference
            audit_module = "quality_scorer"
        elif module == "router":
            response = await BundleRouter(recording).route(
                resource, thresholds.route_confidence_minimum
            )
            rule = RuleDecision(decision=route_bundle(resource))
            state = BundleSerializer().serialize(resource)
            decision = response.category
            confidence = response.confidence
            reference = f"Bundle/{response.bundle_id}"
            audit_module = "bundle_router"
        else:
            response = await NotifiableDiseaseDetector(
                recording, disease_data_path=self._disease_data_path
            ).detect(resource, thresholds.notifiable_confirmed, thresholds.notifiable_review)
            rule = RuleDecision(
                decision="confirmed_notifiable"
                if is_notifiable(resource, self._disease_data_path)
                else "not_notifiable"
            )
            state = ConditionSerializer().serialize(resource)
            decision = response.status
            confidence = response.probability
            reference = f"Condition/{resource.get('id', 'unknown')}"
            audit_module = "notifiable_detector"
        calls = recording.drain()
        if module == "router":
            choice = getattr(calls[0].result, "choice", None)
            override = choice != "unknown" and decision == "unknown"
        truth = None
        jev_correct = rule_correct = None
        entry = self._catalog.get(request.fixture_id) if request.fixture_id else None
        if entry is not None:
            truth = entry.ground_truth
            if module == "quality":
                expected = truth["expected_action"]
                jev_correct = decision == expected
                rule_correct = rule.decision == expected
            elif module == "router":
                expected = truth["expected_category"]
                jev_correct = decision == expected
                rule_correct = rule.decision == expected
            else:
                expected = truth["expected_status"] == "confirmed_notifiable"
                jev_correct = (decision == "confirmed_notifiable") == expected
                rule_correct = (rule.decision == "confirmed_notifiable") == expected
        lane, reason = assign_lane(module, response, thresholds, override)
        # Same labels as the Phase 4 routes, so demo and API decisions share one series.
        record_decision(audit_module, decision, confidence)
        return CompareResponse(
            module=module,
            jev=response,
            jev_decision=decision,
            jev_raw=calls,
            rule=rule,
            ground_truth=truth,
            verdict=Verdict(jev_correct=jev_correct, rule_correct=rule_correct),
            serialized_state=state,
            override_applied=override,
            lane=lane,
            lane_reason=reason,
            audit_event=AuditEventBuilder().build(
                module_name=audit_module,
                decision=decision,
                resource_reference=reference,
                timestamp=datetime.now(UTC),
            ),
            thresholds=thresholds,
            tokens_used=sum(call.result.tokens_used for call in calls),
        )
