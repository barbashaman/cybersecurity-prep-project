"""White-box in-process transport client using FastAPI's TestClient.

Constructing the client builds the application; request handling requires a
reachable ``DATABASE_URL`` because the app lifespan migrates and seeds.
"""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient

from tests.toolkit.clients.protocols import TransportResponse


class InProcessTransportClient:
    """Dispatches HTTP-shaped calls to an in-process FastAPI app."""

    def __init__(self) -> None:
        # Imported lazily so toolkit unit smoke that never calls request() can
        # still import the container without requiring a live database.
        from ecommerce_backoffice_api.presentation.main import create_app

        self._app = create_app()
        self._client = TestClient(self._app)

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> TransportResponse:
        request_kwargs: dict[str, Any] = {
            "method": method.upper(),
            "url": path,
            "headers": headers or {},
        }
        if body is not None:
            request_kwargs["content"] = body.encode("utf-8")
            headers_map = dict(request_kwargs["headers"])
            headers_map.setdefault("content-type", "application/json")
            request_kwargs["headers"] = headers_map
        response = self._client.request(**request_kwargs)
        return TransportResponse(
            status_code=response.status_code,
            headers=dict(response.headers.items()),
            text=response.text,
        )
