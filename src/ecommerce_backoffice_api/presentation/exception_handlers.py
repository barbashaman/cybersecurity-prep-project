"""HTTP exception handlers.

iter-01 (A10) deliberately ships a DEBUG path that echoes full Python
tracebacks into the response body. Remediation replaces this with a global
RFC 9457 problem-details handler that never leaks stack frames.
"""

from __future__ import annotations

import traceback
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from ecommerce_backoffice_api.infrastructure.config import Settings


def build_unhandled_error_response(exc: BaseException, *, debug: bool) -> Response:
    """Build the HTTP body for an unhandled exception.

    VULNERABLE when ``debug`` is True: returns a plain-text traceback including
    the exception type. Secure behaviour (asserted by detection tests) must not
    expose ``Traceback`` markers or exception class names to clients.
    """
    if debug:
        formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return PlainTextResponse(content=formatted, status_code=500)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def register_exception_handlers(application: FastAPI) -> None:
    """Attach the iter-01 DEBUG-leaky unhandled-exception handler."""

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> Response:
        settings = cast(Settings, request.app.state.settings)
        return build_unhandled_error_response(exc, debug=settings.debug)
