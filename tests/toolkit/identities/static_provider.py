"""A placeholder identity provider.

Phase 1 skeleton: returns deterministic, obviously-fake tokens so the DI wiring
and role matrix can be exercised before any real auth exists. Phase 1b replaces
the token source with the API's real login flow (black-box) or an in-process
token issuer (white-box).
"""

from __future__ import annotations

from tests.toolkit.identities.protocols import Identity, IdentityProvider
from tests.toolkit.identities.roles import Role


class StaticIdentityProvider(IdentityProvider):
    """Deterministic identities for wiring and smoke purposes only."""

    def for_role(self, role: Role) -> Identity:
        return Identity(
            role=role,
            subject=f"{role.value}@example.test",
            token=f"phase1-placeholder-token-{role.value}",
        )

    def all_roles(self) -> tuple[Identity, ...]:
        return tuple(self.for_role(role) for role in Role)
