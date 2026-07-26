"""Operational entrypoint for the Jinja2 web service.

Phase 1 serves a single placeholder page plus a ``/health`` probe so the web
tier participates in the version gate and the E2E smoke path. It talks to the
API only over ``API_BASE_URL``; it holds no direct database access. Real
templates and routes arrive in Phase 1b.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def create_app() -> FastAPI:
    version = os.environ.get("VERSION", "0.1.0")
    api_base_url = os.environ.get("API_BASE_URL", "http://api:8000")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    app = FastAPI(title="E-Commerce Backoffice Web", version=version)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"version": version, "api_base_url": api_base_url},
        )

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": version}

    return app


app = create_app()
