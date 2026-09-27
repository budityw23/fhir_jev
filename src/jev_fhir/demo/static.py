"""Static demo UI routes with safe SPA fallback behaviour."""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from jev_fhir.config import Settings


def register_static_routes(app: FastAPI, settings: Settings) -> None:
    """Register demo UI routes that inspect the build output at request time."""

    async def serve_demo(request: Request, path: str = "") -> Response:
        """Serve a contained build asset, or the SPA entrypoint as a fallback."""
        index = settings.demo_web_dist / "index.html"
        dist_root = settings.demo_web_dist.resolve()
        resolved_index = index.resolve()
        if not (resolved_index.is_relative_to(dist_root) and resolved_index.is_file()):
            from jev_fhir.main import _error_response

            return _error_response(request, 503, "ui_not_built", "run make web-build")

        candidate = (settings.demo_web_dist / path).resolve()
        if candidate.is_relative_to(dist_root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(resolved_index)

    @app.get("/demo", include_in_schema=False)
    async def demo_index(request: Request) -> Response:
        """Serve the demo UI entrypoint."""
        return await serve_demo(request)

    @app.get("/demo/{path:path}", include_in_schema=False)
    async def demo_path(request: Request, path: str) -> Response:
        """Serve an asset or provide the demo UI SPA fallback."""
        return await serve_demo(request, path)

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Redirect the application root to the demo UI."""
        return RedirectResponse("/demo", status_code=307)
