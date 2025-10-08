"""
Application entrypoint exposing the FastAPI instance.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import handle_request
from .config import get_settings
from .errors import register_exception_handlers
from .logging import configure_logging


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Dynamic REST Metaservice",
        summary=(
            "A catch-all REST interface that delegates request interpretation to a sandboxed LLM."
        ),
        version="0.1.0",
    )

    if settings.sandbox_deny_net:
        app.extra["sandbox_deny_net"] = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.add_api_route(
        "/{full_path:path}",
        handle_request,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )

    return app


app = create_app()
