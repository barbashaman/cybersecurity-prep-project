"""API composition root and operational entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.startup import prepare_database
from ecommerce_backoffice_api.infrastructure.security.jwt_token_service import JwtTokenService
from ecommerce_backoffice_api.presentation.exception_handlers import register_exception_handlers
from ecommerce_backoffice_api.presentation.routers import (
    admin,
    auth,
    checkout,
    coupons,
    credits,
    orders,
    products,
    revenue,
    stores,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'",
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_allow_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Artifact-Signature"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": resolved.version}

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(stores.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(credits.router, prefix="/api/v1")
    app.include_router(coupons.router, prefix="/api/v1")
    app.include_router(checkout.router, prefix="/api/v1")
    app.include_router(revenue.router, prefix="/api/v1")

    return app


app = create_app()
