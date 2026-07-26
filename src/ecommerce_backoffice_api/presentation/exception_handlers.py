"""HTTP exception handlers (RFC 9457 Problem Details).

iter-01 (A10) remediation: unhandled exceptions never echo Python stack frames
or exception type names to clients. Responses use ``application/problem+json``.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from ecommerce_backoffice_api.infrastructure.config import Settings

_LOGGER = logging.getLogger(__name__)

_PROBLEM_CONTENT_TYPE = "application/problem+json"


def build_unhandled_error_response(exc: BaseException, *, debug: bool) -> Response:
    """Build a safe RFC 9457 problem-details body for an unhandled exception.

    ``debug`` may enrich *server-side* logging only; it must never change the
    client-visible payload to include traceback markers or exception class names.
    """
    _LOGGER.exception(
        "Unhandled exception (debug=%s): %s",
        debug,
        type(exc).__name__,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        media_type=_PROBLEM_CONTENT_TYPE,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred while processing the request.",
        },
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Attach the fail-closed unhandled-exception handler."""

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> Response:
        settings = cast(Settings, request.app.state.settings)
        return build_unhandled_error_response(exc, debug=settings.debug)
