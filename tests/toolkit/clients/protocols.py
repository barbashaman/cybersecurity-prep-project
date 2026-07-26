"""Transport-client port.

The transport client is the seam that lets one Gherkin scenario run black-box
(HTTP against the container) or white-box (in-process against use cases). Both
implementations satisfy :class:`TransportClient`; the DI container decides which
is wired based on the resolved environment.
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """A transport-agnostic response envelope."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""

    def json(self) -> object:
        """Parse the body as JSON. Raises ``ValueError`` on invalid JSON."""
        return _json.loads(self.text)


@runtime_checkable
class TransportClient(Protocol):
    """Issues a request and returns a :class:`TransportResponse`."""

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> TransportResponse:
        """Perform ``method path`` and return the response envelope."""
        ...
