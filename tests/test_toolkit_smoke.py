"""Toolkit self-tests.

These exercise the dependency-injection wiring and the reporting renderer
without requiring a live database. Role-matrix coverage uses
:class:`StaticIdentityProvider` directly so CI quality-gate stays offline-safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.toolkit.clients.http_client import HttpTransportClient
from tests.toolkit.context.container import ToolkitContainer
from tests.toolkit.context.environment import Environment, Transport
from tests.toolkit.identities.roles import Role
from tests.toolkit.identities.static_provider import StaticIdentityProvider
from tests.toolkit.reporting.unified_report import build_summary


def test_container_builds_http_context() -> None:
    environment = Environment(transport=Transport.HTTP, base_url="http://api:8000")
    context = ToolkitContainer(
        environment,
        use_static_identities=True,
    ).build_execution_context()

    assert context.environment.transport is Transport.HTTP
    assert context.environment.base_url == "http://api:8000"
    assert isinstance(context.client, HttpTransportClient)


def test_role_matrix_has_all_four_roles() -> None:
    identities = StaticIdentityProvider().all_roles()
    roles = {identity.role for identity in identities}

    assert roles == set(Role)
    assert len(identities) == 4


def test_invalid_transport_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOOLKIT_TRANSPORT", "carrier-pigeon")
    try:
        Environment.from_process_env()
    except ValueError as exc:
        assert "carrier-pigeon" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("Invalid transport should raise ValueError.")


def test_unified_report_handles_empty_suite() -> None:
    summary = build_summary(robot_paths=[], junit_paths=[Path("does-not-exist.xml")])

    assert summary.total == 0
    assert summary.success_rate == 100.0
