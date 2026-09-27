"""Demo API tests using the deterministic mock client."""

import json
from pathlib import Path
from shutil import copy
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient
from fhir.resources.R4B.auditevent import AuditEvent

from jev_fhir.baselines.quality import score_observation
from jev_fhir.config import Settings
from jev_fhir.demo.catalog import FixtureCatalog
from jev_fhir.main import create_app
from jev_fhir.routes.demo import _parse_last_event_id


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


def test_sse_endpoint_replays_pipeline_events_in_wire_format() -> None:
    import time

    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/demo/pipeline/run",
            json={"source": "unit", "modules": ["router"], "rate_per_s": None},
        ).json()
        feed = app.state.services.demo.feed
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if any(
                event.run_id == started["run_id"] and event.status == "finished"
                for _, event in feed.since(0)
                if hasattr(event, "status")
            ):
                break
            time.sleep(0.02)
        response = client.get(
            "/api/v1/demo/decisions/stream?limit=3", headers={"Last-Event-ID": "0"}
        )
        assert response.status_code == 200
        assert response.text.count("event: ") == 3
        assert all(block.startswith("id: ") for block in response.text.strip().split("\n\n"))


def test_sse_endpoint_replays_only_events_newer_than_last_event_id_and_has_headers() -> None:
    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(app) as client:
        feed = app.state.services.demo.feed
        for index in range(3):
            compare(client, "quality", "tests/fixtures/patients/complete_patient.json")
            assert feed.since(0)[-1][0] == index + 1
        response = client.get(
            "/api/v1/demo/decisions/stream?limit=2", headers={"Last-Event-ID": "1"}
        )
        assert [line for line in response.text.splitlines() if line.startswith("id: ")] == [
            "id: 2",
            "id: 3",
        ]
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["X-Accel-Buffering"] == "no"


def test_sse_endpoint_formats_run_events_and_validates_limit() -> None:
    from jev_fhir.demo.feed import RunEvent

    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(app) as client:
        app.state.services.demo.feed.publish(
            RunEvent(run_id="run-1", status="started", total=1, processed=0)
        )
        response = client.get(
            "/api/v1/demo/decisions/stream?limit=1", headers={"Last-Event-ID": "0"}
        )
        assert "event: run\n" in response.text
        assert client.get("/api/v1/demo/decisions/stream?limit=0").status_code == 422


def test_invalid_last_event_id_is_treated_as_absent() -> None:
    assert _parse_last_event_id("not-an-integer") is None
    assert _parse_last_event_id("-1") is None
    assert _parse_last_event_id(None) is None
    assert _parse_last_event_id("12") == 12


def test_benchmark_list_is_newest_first_and_old_reports_default_dataset(tmp_path: Path) -> None:
    """Benchmark reports ignore non-reports and preserve pre-D0.5 compatibility."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    reports_root = Path("benchmarks/results")
    copy(reports_root / "bench_20260924T083443Z.json", results_dir)
    copy(reports_root / "bench_20260924T154552Z.json", results_dir)
    (results_dir / "bench_20260924T154552Z.md").write_text("ignore me")
    (results_dir / "bench_20260924T160000Z.json").write_text("not json")
    (results_dir / "bench_20260924T160001Z.json").write_text("[]")
    settings = Settings(mock_jev=True, demo_enabled=True, demo_results_dir=results_dir)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/demo/benchmarks")
        assert response.status_code == 200
        reports = response.json()
        assert [report["name"] for report in reports] == [
            "bench_20260924T154552Z",
            "bench_20260924T083443Z",
        ]
        assert reports[-1]["dataset"] == "unit"
        assert reports[-1]["jev_model"] is None
        raw_report = client.get("/api/v1/demo/benchmarks/bench_20260924T154552Z")
        assert raw_report.status_code == 200 and raw_report.json()["dataset"] == "unit"
        assert client.get("/api/v1/demo/benchmarks/nope").status_code == 404
        assert client.get("/api/v1/demo/benchmarks/../../pyproject").status_code == 404


def test_benchmark_missing_directory_and_bad_names_never_read_files(tmp_path: Path) -> None:
    """Invalid report names are rejected before any file in a real directory is read."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    copy(Path("benchmarks/results/bench_20260924T083443Z.json"), results_dir)
    (results_dir / "notes.json").write_text('{"secret": true}')
    settings = Settings(mock_jev=True, demo_enabled=True, demo_results_dir=results_dir)
    with TestClient(create_app(settings)) as client:
        valid = client.get("/api/v1/demo/benchmarks/bench_20260924T083443Z")
        assert valid.status_code == 200
        with patch("pathlib.Path.read_text", side_effect=AssertionError("must not read")):
            for name in ("notes", "bench_20260924T083443Z.txt", "nope"):
                response = client.get(f"/api/v1/demo/benchmarks/{name}")
                assert response.status_code == 404
                assert response.json()["error"] == "not_found"
                assert "secret" not in response.text


def test_benchmark_missing_directory_and_report_return_empty_or_404(tmp_path: Path) -> None:
    """Missing report directories are empty, while a valid absent report is a structured 404."""
    settings = Settings(mock_jev=True, demo_enabled=True, demo_results_dir=tmp_path / "missing")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/demo/benchmarks").json() == []
        absent = client.get("/api/v1/demo/benchmarks/bench_20990101T000000Z")
        assert absent.status_code == 404
        assert absent.json()["error"] == "not_found"
        traversal = client.get("/api/v1/demo/benchmarks/%2e%2e%2fbench_20260924T083443Z")
        assert traversal.status_code == 404


def test_static_ui_serves_assets_and_never_serves_traversal_paths(tmp_path: Path) -> None:
    """The demo UI serves contained files and returns its SPA fallback for traversal."""
    dist_dir = tmp_path / "dist"
    assets = dist_dir / "assets"
    assets.mkdir(parents=True)
    index = "<!doctype html><title>demo app</title>"
    (dist_dir / "index.html").write_text(index)
    (assets / "app.js").write_text("console.log('asset')")
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")
    (dist_dir / "leak.txt").symlink_to(secret)
    settings = Settings(mock_jev=True, demo_enabled=True, demo_web_dist=dist_dir)
    with TestClient(create_app(settings)) as client:
        assert client.get("/demo/studio").text == index
        assert client.get("/demo/assets/app.js").text == "console.log('asset')"
        for path in ("%2e%2e/secret.txt", "..%2fsecret.txt", "leak.txt"):
            response = client.get(f"/demo/{path}")
            assert response.request.url.path.startswith("/demo/")
            assert response.text == index
            assert "TOP-SECRET" not in response.text


def test_static_ui_is_built_at_request_time_and_root_redirects(tmp_path: Path) -> None:
    """A missing build gives the contract error until index.html appears without restart."""
    dist_dir = tmp_path / "dist"
    settings = Settings(mock_jev=True, demo_enabled=True, demo_web_dist=dist_dir)
    with TestClient(create_app(settings)) as client:
        missing = client.get("/demo")
        assert missing.status_code == 503
        assert missing.json()["error"] == "ui_not_built"
        assert missing.json()["detail"] == "run make web-build"
        assert missing.json()["request_id"] == missing.headers["X-Request-Id"]
        redirect = client.get("/", follow_redirects=False)
        assert redirect.status_code == 307 and redirect.headers["location"] == "/demo"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("built now")
        assert client.get("/demo").text == "built now"


def test_static_routes_do_not_exist_when_demo_is_disabled() -> None:
    """Demo disabled leaves the application root and demo UI paths absent."""
    with TestClient(create_app(Settings(mock_jev=True))) as client:
        assert client.get("/").status_code == 404
        assert client.get("/demo").status_code == 404


def test_demo_cors_is_enabled_only_for_configured_origins() -> None:
    """Demo CORS answers allowed preflights and exposes request timing headers."""
    enabled = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(enabled) as client:
        allowed = client.options(
            "/api/v1/demo/config",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        rejected = client.options(
            "/api/v1/demo/config",
            headers={"Origin": "https://example.invalid", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in rejected.headers
        actual = client.get("/api/v1/demo/config", headers={"Origin": "http://localhost:5173"})
        assert "X-Request-Id" in actual.headers["access-control-expose-headers"]
    with TestClient(create_app(Settings(mock_jev=True))) as client:
        disabled = client.options(
            "/api/v1/demo/config",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in disabled.headers


def test_phase4_response_schemas_match_snapshot_with_demo_both_ways() -> None:
    """D1e must not alter the three public Phase 4 response schema contracts."""
    expected = json.loads(Path("tests/snapshots/phase4_response_schemas.json").read_text())
    for demo_enabled in (False, True):
        schemas = create_app(Settings(mock_jev=True, demo_enabled=demo_enabled)).openapi()[
            "components"
        ]["schemas"]
        actual = {
            name: schemas[name]
            for name in (
                "QualityScoreResponse",
                "BundleRouteResponse",
                "NotifiableDetectionResponse",
            )
        }
        assert actual == expected
