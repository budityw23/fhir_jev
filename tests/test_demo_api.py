"""D1a app wiring tests; demo HTTP endpoints are deferred to D1b."""

from fastapi.testclient import TestClient

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


def test_demo_enabled_builds_catalog_and_mounts_empty_router() -> None:
    app = create_app(Settings(mock_jev=True, demo_enabled=True))
    with TestClient(app):
        assert isinstance(app.state.services.demo.catalog, FixtureCatalog)
        assert not any(path.startswith("/api/v1/demo") for path in app.openapi()["paths"])
