"""Black-box HTTP transport client (skeleton).

Phase 1 declares the type and constructor only. The concrete HTTP call is wired
in Phase 1b (httpx / Playwright APIRequestContext) so that the request/response
recording needed by the security suites is added in one place.
"""

from __future__ import annotations

from tests.toolkit.clients.protocols import TransportResponse


class HttpTransportClient:
    """Issues real HTTP requests against a running container."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

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
        raise NotImplementedError("HttpTransportClient is a Phase 1 skeleton; wired in Phase 1b.")
