"""White-box in-process transport client (skeleton).

Dispatches calls directly to in-process use cases instead of crossing the
network, so the same scenario becomes a white-box test. Wired in Phase 1b once
the application composition root exists.
"""

from __future__ import annotations

from tests.toolkit.clients.protocols import TransportResponse


class InProcessTransportClient:
    """Invokes use cases in-process, bypassing HTTP."""

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> TransportResponse:
        raise NotImplementedError(
            "InProcessTransportClient is a Phase 1 skeleton; wired in Phase 1b."
        )
