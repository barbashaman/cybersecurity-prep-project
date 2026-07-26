"""API composition root and operational entrypoint.

Phase 1b wires the e-commerce baseline (auth, RBAC, CRUD) while keeping DEBUG,
CORS, and OpenAPI docs deliberately permissive — the hardening vehicle for
iter-09 (A02 Security Misconfiguration).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.startup import prepare_database
from ecommerce_backoffice_api.infrastructure.security.jwt_token_service import JwtTokenService
from ecommerce_backoffice_api.presentation.exception_handlers import register_exception_handlers
from ecommerce_backoffice_api.presentation.routers import auth, orders, products, stores


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine, session_factory = prepare_database(resolved)
        application.state.settings = resolved
        application.state.engine = engine
        application.state.session_factory = session_factory
        application.state.token_service = JwtTokenService(
            secret=resolved.jwt_secret,
            algorithm=resolved.jwt_algorithm,
            expire_minutes=resolved.jwt_expire_minutes,
        )
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="E-Commerce Backoffice API",
        version=resolved.version,
        description=(
            "Phase 1b baseline application: JWT auth, RBAC, store/product/order "
            "CRUD against PostgreSQL. OWASP Top 10:2025 countdown iterations follow."
        ),
        # Never enable framework debug pages — they leak stack frames to clients.
        # Application DEBUG still drives server-side logging verbosity (iter-09).
        debug=False,
        # Per-environment Swagger exposure policy (tightened in iter-09).
        docs_url="/docs" if resolved.expose_docs else None,
        redoc_url="/redoc" if resolved.expose_docs else None,
        openapi_url="/openapi.json" if resolved.expose_docs else None,
        lifespan=lifespan,
    )
    # Settings must be readable by exception handlers even before lifespan runs.
    app.state.settings = resolved
    register_exception_handlers(app)

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

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(stores.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(orders.router, prefix="/api/v1")

    return app


app = create_app()
