"""Resolved test environment.

Read once from the process environment and injected (never read ad hoc deep in
a test). ``Transport`` selects black-box vs white-box execution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class Transport(str, Enum):
    """Execution transport for the toolkit."""

    HTTP = "http"
    IN_PROCESS = "in_process"


@dataclass(frozen=True, slots=True)
class Environment:
    """Everything the toolkit needs to know about where it is running."""

    transport: Transport
    base_url: str

    @classmethod
    def from_process_env(cls) -> Environment:
        """Build an :class:`Environment` from ``TOOLKIT_*`` variables."""
        raw_transport = os.environ.get("TOOLKIT_TRANSPORT", Transport.HTTP.value)
        try:
            transport = Transport(raw_transport)
        except ValueError as exc:
            valid = ", ".join(member.value for member in Transport)
            raise ValueError(
                f"TOOLKIT_TRANSPORT='{raw_transport}' is invalid; expected one of: {valid}."
            ) from exc
        base_url = os.environ.get("TOOLKIT_BASE_URL", "http://localhost:8000")
        return cls(transport=transport, base_url=base_url)
