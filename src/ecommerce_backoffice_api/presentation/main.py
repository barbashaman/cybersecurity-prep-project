"""Operational entrypoint for the API service.

Phase 1 exposes only the operational contract the DevSecOps machinery needs to
test itself - a ``/health`` probe carrying the version (consumed by the version
gate) and the auto-generated OpenAPI document at ``/openapi.json`` / ``/docs``
(consumed by the ZAP API scan and contract tests). No e-commerce domain or
business logic lives here; that arrives in Phase 1b.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecommerce_backoffice_api.infrastructure.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()

    app = FastAPI(
        title="E-Commerce Backoffice API",
        version=resolved.version,
        description=(
            "Operational baseline (Phase 1). E-commerce endpoints arrive in "
            "Phase 1b; the OWASP Top 10:2025 countdown follows."
        ),
        # Per-environment Swagger exposure policy (tightened in iter-09).
        docs_url="/docs" if resolved.expose_docs else None,
        redoc_url="/redoc" if resolved.expose_docs else None,
        openapi_url="/openapi.json" if resolved.expose_docs else None,
    )

    # Deliberately permissive baseline; the strict allowlist lands in iter-09.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_allow_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": resolved.version}

    return app


app = create_app()
