"""Jinja2 web tier for the Phase 1b e-commerce backoffice.

Talks to the API only over ``API_BASE_URL``; holds no direct database access.
The JWT from login is stored in a signed session cookie.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ecommerce_backoffice_web.api_client import ApiClient, ApiClientError

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"
_SESSION_ACCESS_TOKEN_KEY = "access_token"  # nosec B105  # noqa: S105 - cookie key name, not a secret
_SESSION_ROLE_KEY = "role"
_SESSION_EMAIL_KEY = "email"


def create_app() -> FastAPI:
    version = os.environ.get("VERSION", "0.1.0")
    api_base_url = os.environ.get("API_BASE_URL", "http://api:8000")
    # nosec B105 - demo session secret for Phase 1b; hardened later with iter-09.
    session_secret = os.environ.get(
        "WEB_SESSION_SECRET",
        "phase1b-demo-only-web-session-secret",
    )
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    api_client = ApiClient(api_base_url)

    app = FastAPI(title="E-Commerce Backoffice Web", version=version)
    # Remediated (A04): Secure session cookies + HSTS.
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        https_only=True,
    )
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Emit CSP (A05) and HSTS (A04) on every response."""
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _context(request: Request, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "request": request,
            "version": version,
            "api_base_url": api_base_url,
            "email": request.session.get(_SESSION_EMAIL_KEY),
            "role": request.session.get(_SESSION_ROLE_KEY),
        }
        payload.update(extra)
        return payload

    def _require_token(request: Request) -> str | RedirectResponse:
        token = request.session.get(_SESSION_ACCESS_TOKEN_KEY)
        if not isinstance(token, str) or not token:
            return RedirectResponse(url="/login", status_code=303)
        return token

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": version}

    @app.get("/", response_model=None)
    def home(request: Request) -> RedirectResponse:
        if request.session.get(_SESSION_ACCESS_TOKEN_KEY):
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/login", response_class=HTMLResponse, response_model=None)
    def login_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "login.html",
            _context(request, error=None),
        )

    @app.post("/login", response_class=HTMLResponse, response_model=None)
    def login_submit(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        try:
            result = api_client.login(email=email, password=password)
        except ApiClientError as error:
            return templates.TemplateResponse(
                request,
                "login.html",
                _context(request, error=error.detail),
                status_code=400,
            )
        access_token = result.get("access_token")
        role = result.get("role")
        if not isinstance(access_token, str) or not isinstance(role, str):
            return templates.TemplateResponse(
                request,
                "login.html",
                _context(request, error="Login response was incomplete."),
                status_code=500,
            )
        request.session[_SESSION_ACCESS_TOKEN_KEY] = access_token
        request.session[_SESSION_ROLE_KEY] = role
        request.session[_SESSION_EMAIL_KEY] = email.strip().lower()
        return RedirectResponse(url="/dashboard", status_code=303)

    @app.post("/logout")
    def logout(request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/dashboard", response_class=HTMLResponse, response_model=None)
    def dashboard(request: Request) -> Response:
        token = _require_token(request)
        if isinstance(token, RedirectResponse):
            return token
        try:
            stores = api_client.list_stores(token)
        except ApiClientError as error:
            return templates.TemplateResponse(
                request,
                "dashboard.html",
                _context(request, stores=[], error=error.detail),
                status_code=error.status_code,
            )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _context(request, stores=stores, error=None),
        )

    @app.get("/stores/{store_id}", response_class=HTMLResponse, response_model=None)
    def store_detail(request: Request, store_id: int) -> Response:
        token = _require_token(request)
        if isinstance(token, RedirectResponse):
            return token
        search_query = request.query_params.get("q", "")
        try:
            store = api_client.get_store(token, store_id)
            if search_query:
                # VULNERABLE (A05): forwards ``q`` to the SQL-concat search API.
                products = api_client.search_products(token, store_id, search_query)
            else:
                products = api_client.list_products(token, store_id)
        except ApiClientError as error:
            return templates.TemplateResponse(
                request,
                "store_detail.html",
                _context(
                    request,
                    store={"id": store_id, "name": f"Store {store_id}"},
                    products=[],
                    search_query=search_query,
                    error=error.detail,
                ),
                status_code=error.status_code,
            )
        return templates.TemplateResponse(
            request,
            "store_detail.html",
            _context(
                request,
                store=store,
                products=products,
                search_query=search_query,
                error=None,
            ),
        )

    @app.get("/stores/{store_id}/orders", response_class=HTMLResponse, response_model=None)
    def store_orders(request: Request, store_id: int) -> Response:
        token = _require_token(request)
        if isinstance(token, RedirectResponse):
            return token
        try:
            store = api_client.get_store(token, store_id)
            orders = api_client.list_orders(token, store_id)
        except ApiClientError as error:
            return templates.TemplateResponse(
                request,
                "orders.html",
                _context(
                    request,
                    store={"id": store_id, "name": f"Store {store_id}"},
                    orders=[],
                    error=error.detail,
                ),
                status_code=error.status_code,
            )
        return templates.TemplateResponse(
            request,
            "orders.html",
            _context(request, store=store, orders=orders, error=None),
        )

    return app


app = create_app()
