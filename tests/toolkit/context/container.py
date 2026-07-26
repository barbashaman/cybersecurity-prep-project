"""Composition root for the test toolkit.

A tiny, explicit DI container - no framework. It reads the environment, selects
the transport implementation from :class:`Transport`, and assembles the
:class:`ExecutionContext`. This is the single place that knows how the pieces
fit together.
"""

from __future__ import annotations

from tests.toolkit.clients.http_client import HttpTransportClient
from tests.toolkit.clients.in_process_client import InProcessTransportClient
from tests.toolkit.clients.protocols import TransportClient
from tests.toolkit.context.environment import Environment, Transport
from tests.toolkit.context.execution_context import ExecutionContext
from tests.toolkit.identities.login_provider import LoginIdentityProvider
from tests.toolkit.identities.protocols import IdentityProvider
from tests.toolkit.identities.static_provider import StaticIdentityProvider


class ToolkitContainer:
    """Builds an :class:`ExecutionContext` from a resolved environment."""

    def __init__(
        self,
        environment: Environment | None = None,
        *,
        use_static_identities: bool = False,
    ) -> None:
        self._environment = environment or Environment.from_process_env()
        self._use_static_identities = use_static_identities

    def _build_client(self) -> TransportClient:
        if self._environment.transport is Transport.HTTP:
            return HttpTransportClient(base_url=self._environment.base_url)
        return InProcessTransportClient()

    def _build_identity_provider(self, client: TransportClient) -> IdentityProvider:
        if self._use_static_identities:
            return StaticIdentityProvider()
        return LoginIdentityProvider(client)

    def build_execution_context(self) -> ExecutionContext:
        client = self._build_client()
        return ExecutionContext(
            environment=self._environment,
            identities=self._build_identity_provider(client),
            client=client,
        )
