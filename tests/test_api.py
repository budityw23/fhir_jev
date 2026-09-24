"""Phase 4 integration tests for the FastAPI decision-layer API."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from jev_fhir.config import Settings
from jev_fhir.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> dict[str, Any]:
    """Load a checked-in FHIR fixture."""
    return cast(dict[str, Any], json.loads((FIXTURES / relative_path).read_text()))


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    """Run the API lifespan with its deterministic offline Jev client."""
    with TestClient(create_app(Settings(mock_jev=True))) as client:
        yield client


def assert_request_headers(response: Any) -> None:
    """Check the headers supplied by Phase 4 middleware."""
    assert response.headers["X-Request-Id"]
    assert float(response.headers["X-Request-Duration-Ms"]) >= 0


def test_quality_score_endpoint_returns_quality_response(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/quality-score",
        json={
            "resource_type": "Patient",
            "resource": load_fixture("patients/complete_patient.json"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "auto_accept"
    assert body["nik_valid"] is True
    assert body["resource_reference"] == "Patient/12345"
    assert_request_headers(response)


def test_quality_score_rejects_unsupported_resource_type(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/quality-score",
        json={
            "resource_type": "Condition",
            "resource": load_fixture("conditions/dengue_a90.json"),
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    assert_request_headers(response)


def test_route_bundle_endpoint_returns_bundle_route(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/route-bundle", json={"bundle": load_fixture("bundles/lab_bundle.json")}
    )

    assert response.status_code == 200
    assert response.json()["category"] == "lab_result"
    assert_request_headers(response)


def test_route_bundle_returns_structured_error_for_invalid_resource(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/route-bundle", json={"bundle": load_fixture("patients/minimal_patient.json")}
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert response.json()["request_id"] == response.headers["X-Request-Id"]


def test_notifiable_endpoint_returns_detection_and_flag(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/detect-notifiable",
        json={"condition": load_fixture("conditions/dengue_a90.json")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed_notifiable"
    assert body["flag_resource"]["resourceType"] == "Flag"
    assert_request_headers(response)


def test_notifiable_endpoint_rejects_wrong_fhir_type(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/detect-notifiable",
        json={"condition": load_fixture("patients/minimal_patient.json")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


def test_health_reports_mock_client(api_client: TestClient) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "jev_client": "mock",
        "jev_model": None,
        "version": "0.1.0",
    }
    assert_request_headers(response)


def test_metrics_are_prometheus_formatted(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/route-bundle", json={"bundle": load_fixture("bundles/lab_bundle.json")}
    )
    response = api_client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "jev_fhir_http_requests_total" in response.text
    assert "jev_fhir_decisions_total" in response.text


def test_malformed_json_returns_structured_422(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/quality-score",
        content="{invalid-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error", "detail", "request_id", "timestamp"}
    assert body["request_id"] == response.headers["X-Request-Id"]
