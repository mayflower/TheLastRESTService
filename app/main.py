"""
Application entrypoint exposing the FastAPI instance.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import handle_request
from .config import get_settings
from .errors import register_exception_handlers
from .logging import configure_logging
from .security import SessionContext, session_dependency


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

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        """Root endpoint with helpful hints."""
        return {
            "message": "The Last REST Service™",
            "tagline": "Because writing REST APIs is so 2023",
            "docs": "/docs",
            "swagger": "/swagger.json",
            "health": "/healthz",
            "hint": "Just start POSTing to any endpoint. See what happens. We dare you.",
        }

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/swagger.json", tags=["meta"])
    async def swagger_json(session: SessionContext = Depends(session_dependency)) -> dict:
        """
        Generate OpenAPI spec based on what you've actually used.

        This endpoint returns a dynamically-generated OpenAPI 3.0 specification
        that reflects the resources YOU have created in YOUR session.

        Different sessions see different specs. Because your API is personal.
        """
        from .openapi_generator import generate_openapi_spec

        return generate_openapi_spec(session.id)

    app.add_api_route(
        "/{full_path:path}",
        handle_request,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )

    return app


app = create_app()
