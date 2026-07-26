"""Black-box HTTP transport client backed by httpx."""

from __future__ import annotations

import httpx

from tests.toolkit.clients.protocols import TransportResponse


class HttpTransportClient:
    """Issues real HTTP requests against a running container or host."""

    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def base_url(self) -> str:
        return self._base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> TransportResponse:
        url = f"{self._base_url}{path}"
        request_headers = dict(headers or {})
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                content=body,
            )
        return TransportResponse(
            status_code=response.status_code,
            headers=dict(response.headers.items()),
            text=response.text,
        )
