"""Domain-aware assertion helpers (skeleton).

Kept separate from raw ``assert`` so security-relevant expectations (status
codes, absence of PII, presence of security headers) read declaratively at the
call site. Bodies land in Phase 1b alongside the first real scenarios.
"""

from __future__ import annotations

from tests.toolkit.clients.protocols import TransportResponse


def assert_status(response: TransportResponse, expected: int) -> None:
    """Assert the response status code equals ``expected``."""
    if response.status_code != expected:
        raise AssertionError(f"Expected status {expected} but received {response.status_code}.")


def assert_header_present(response: TransportResponse, header: str) -> None:
    """Assert a (case-insensitive) header is present on the response."""
    lowered = {key.lower() for key in response.headers}
    if header.lower() not in lowered:
        raise AssertionError(f"Expected header '{header}' to be present.")
