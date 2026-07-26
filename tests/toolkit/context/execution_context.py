"""The dependency-injected execution context.

``ExecutionContext`` is constructor-injected with a resolved environment, an
identity provider and a transport client. Holding these three together behind
one object is what lets a scenario stay ignorant of whether it is talking to a
container over HTTP or to in-process use cases.
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.toolkit.clients.protocols import TransportClient
from tests.toolkit.context.environment import Environment
from tests.toolkit.identities.protocols import Identity, IdentityProvider
from tests.toolkit.identities.roles import Role


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable bundle of the collaborators a scenario needs."""

    environment: Environment
    identities: IdentityProvider
    client: TransportClient

    def as_role(self, role: Role) -> Identity:
        """Resolve the identity for ``role`` from the injected provider."""
        return self.identities.for_role(role)
