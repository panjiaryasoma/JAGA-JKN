"""Same-origin frontend, reusing the existing API and its error boundaries."""

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from apps.api.config import Settings
from apps.api.main import create_app as create_api

STATIC = Path(__file__).with_name("static")


def create_app(settings: Settings | None = None):
    application = create_api(settings)

    @application.middleware("http")
    async def frontend_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        return response

    @application.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html", media_type="text/html")

    application.mount("/assets", StaticFiles(directory=STATIC), name="web-assets")
    return application


app = create_app()
