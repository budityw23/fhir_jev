"""D1b demo compare API tests using the deterministic mock client."""

from typing import Any, cast

from fastapi.testclient import TestClient
from fhir.resources.R4B.auditevent import AuditEvent

from jev_fhir.baselines.quality import score_observation
from jev_fhir.config import Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.main import create_app


def test_demo_disabled_has_no_services_or_routes() -> None:
    app = create_app(Settings(mock_jev=True, demo_enabled=False))
    with TestClient(app):
        assert app.state.services.demo is None
        assert not any(
            getattr(route, "path", "").startswith("/api/v1/demo") for route in app.routes
        )
        assert not any(path.startswith("/api/v1/demo") for path in app.openapi()["paths"])


def test_demo_enabled_builds_catalog_and_mounts_routes() -> None:
    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(app):
        assert isinstance(app.state.services.demo.catalog, FixtureCatalog)
        assert "/api/v1/demo/config" in app.openapi()["paths"]


def test_config_and_fixture_filters_have_contract_shape() -> None:
    with TestClient(create_app(Settings(mock_jev=True, demo_enabled=True))) as client:
        config = client.get("/api/v1/demo/config")
        assert config.status_code == 200 and config.json()["mode"] == "mock"
        assert len(config.json()["thresholds"]) == 4 and len(config.json()["route_options"]) == 5
        fixtures = client.get("/api/v1/demo/fixtures", params={"source": "hard"})
        assert fixtures.status_code == 200 and len(fixtures.json()) >= 25
        assert client.get("/api/v1/demo/fixtures", params={"source": "nope"}).status_code == 422


def demo_client() -> TestClient:
    return TestClient(create_app(Settings(mock_jev=True, demo_enabled=True)))


def compare(
    client: TestClient, module: str, fixture_id: str, thresholds: dict[str, float] | None = None
) -> dict[str, Any]:
    """Load an allow-listed fixture and compare it, sending its id so ground truth is attached."""
    resource = client.get(f"/api/v1/demo/fixtures/{fixture_id}").json()
    body: dict[str, Any] = {"resource": resource, "fixture_id": fixture_id}
    if thresholds is not None:
        body["thresholds"] = thresholds
    response = client.post(f"/api/v1/demo/compare/{module}", json=body)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_fixture_errors_are_structured_but_unknown_routes_stay_default() -> None:
    with demo_client() as client:
        response = client.get("/api/v1/demo/fixtures/not-a-catalog-id")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "not_found"
        assert body["request_id"] == response.headers["X-Request-Id"]
        assert "X-Request-Duration-Ms" in response.headers
        unknown = client.get("/api/v1/nope")
        assert unknown.status_code == 404 and unknown.json() == {"detail": "Not Found"}


def test_fixture_traversal_returns_404_and_never_env_content() -> None:
    """Contract: `/fixtures/../../.env` and `/fixtures/%2e%2e/.env` → 404; `.env` never returned.

    The HTTP client normalises a literal `../` before sending, so that request never reaches the
    fixture route; the percent-encoded forms do reach it (as the id "../../.env"), and the
    ErrorResponse body proves the allow-list rejected them.
    """
    with demo_client() as client:
        literal = client.get("/api/v1/demo/fixtures/../../.env")
        assert literal.status_code == 404 and "JEV_API_KEY" not in literal.text
        for encoded in ("%2e%2e/%2e%2e/.env", "%2e%2e/.env", "..%2f..%2f.env"):
            response = client.get(f"/api/v1/demo/fixtures/{encoded}")
            assert response.status_code == 404, encoded
            assert response.request.url.path.startswith("/api/v1/demo/fixtures/"), encoded
            assert response.json()["error"] == "not_found", encoded
            assert "JEV_API_KEY" not in response.text, encoded


def test_compare_quality_complete_patient() -> None:
    with demo_client() as client:
        result = compare(client, "quality", "tests/fixtures/patients/complete_patient.json")
        assert result["jev_decision"] == "auto_accept"
        assert result["rule"]["decision"] in {"auto_accept", "review_needed"}
        assert "field_completeness" in result["serialized_state"]
        assert [call["primitive"] for call in result["jev_raw"]] == ["score", "noul"]
        assert result["tokens_used"] == sum(
            call["result"]["tokens_used"] for call in result["jev_raw"]
        )
        assert result["tokens_used"] > 0
        AuditEvent.model_validate(result["audit_event"])
        assert "type" in result["audit_event"] and "code" not in result["audit_event"]


def test_compare_router_mixed_bundle_with_high_floor_is_overridden() -> None:
    with demo_client() as client:
        result = compare(
            client,
            "router",
            "tests/fixtures/bundles/mixed_bundle.json",
            {"route_confidence_minimum": 0.99},
        )
        assert result["jev"]["category"] == "unknown"
        assert result["override_applied"] is True
        assert result["lane"] == "review"
        assert result["lane_reason"].startswith("confidence")
        assert result["thresholds"]["route_confidence_minimum"] == 0.99


def test_compare_notifiable_japanese_encephalitis_is_flagged() -> None:
    with demo_client() as client:
        result = compare(
            client, "notifiable", "tests/fixtures/conditions/japanese_encephalitis_a83.json"
        )
        assert result["lane"] == "flagged"
        assert result["jev"]["flag_resource"] is not None
        assert result["verdict"]["jev_correct"] is True
        AuditEvent.model_validate(result["audit_event"])


def test_compare_quality_invalid_nik_is_gated() -> None:
    """The completeness score passes, so the NIK gate is what sends this patient to review."""
    with demo_client() as client:
        result = compare(client, "quality", "tests/fixtures/patients/invalid_nik.json")
        assert result["jev"]["score"] >= result["thresholds"]["quality_threshold"]
        assert result["jev"]["nik_valid"] is False
        assert result["jev_decision"] == "review_needed"
        assert result["rule"]["decision"] == "review_needed"
        assert result["lane"] == "review"
        assert result["lane_reason"].startswith("NIK gate failed")


def test_compare_quality_observation_uses_observation_baseline() -> None:
    fixture_id = "tests/fixtures/observations/missing_value.json"
    with demo_client() as client:
        result = compare(client, "quality", fixture_id)
        resource = client.get(f"/api/v1/demo/fixtures/{fixture_id}").json()
        assert result["rule"]["score"] == score_observation(resource)["score"]
        assert result["rule"]["nik_valid"] is None
        assert [call["primitive"] for call in result["jev_raw"]] == ["score"]


def test_bad_threshold_override_returns_validation_error() -> None:
    with TestClient(create_app(Settings(mock_jev=True, demo_enabled=True))) as client:
        patient = client.get(
            "/api/v1/demo/fixtures/tests/fixtures/patients/complete_patient.json"
        ).json()
        response = client.post(
            "/api/v1/demo/compare/quality",
            json={
                "resource": patient,
                "thresholds": {"notifiable_confirmed": 0.2, "notifiable_review": 0.8},
            },
        )
        assert response.status_code == 422


def test_compare_publishes_decision_event() -> None:
    fixture_id = "tests/fixtures/patients/complete_patient.json"
    with demo_client() as client:
        compare(client, "quality", fixture_id)
        events = client.get("/api/v1/demo/decisions").json()
        assert len(events) == 1
        assert events[0]["run_id"] is None and events[0]["fixture_id"] == fixture_id


def test_decision_limit_and_sequence_contract() -> None:
    with demo_client() as client:
        compare(client, "quality", "tests/fixtures/patients/complete_patient.json")
        compare(client, "router", "tests/fixtures/bundles/mixed_bundle.json")
        compare(
            client,
            "notifiable",
            "tests/fixtures/conditions/japanese_encephalitis_a83.json",
        )
        body = client.get("/api/v1/demo/decisions", params={"limit": 3}).json()
        assert len(body) == 3
        assert [item["seq"] for item in body] == sorted(
            (item["seq"] for item in body), reverse=True
        )
        assert client.get("/api/v1/demo/decisions", params={"limit": 0}).status_code == 422
        assert client.get("/api/v1/demo/decisions", params={"limit": 501}).status_code == 422


def test_pipeline_api_unit_run_completes_with_its_total() -> None:
    import time

    with demo_client() as client:
        started = client.post(
            "/api/v1/demo/pipeline/run",
            json={"source": "unit", "modules": ["router"], "rate_per_s": None},
        )
        assert started.status_code == 200, started.text
        run = started.json()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            events = client.get("/api/v1/demo/decisions", params={"limit": 500}).json()
            decisions = [event for event in events if event["run_id"] == run["run_id"]]
            if len(decisions) == run["total"]:
                break
            time.sleep(0.02)
        assert len(decisions) == run["total"]


def test_pipeline_stop_unknown_run_is_structured_not_found() -> None:
    with demo_client() as client:
        response = client.post("/api/v1/demo/pipeline/no-such-run/stop")
        assert response.status_code == 404
        assert response.json()["error"] == "not_found"
