"""Identity-provider port.

The identity provider supplies the multi-role token matrix. Declared as a
Protocol so a black-box provider (real login against the container) and a
white-box provider (in-process token minting) are interchangeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from tests.toolkit.identities.roles import Role


@dataclass(frozen=True, slots=True)
class Identity:
    """A resolved identity: a role plus the credential material to act as it."""

    role: Role
    subject: str
    token: str


@runtime_checkable
class IdentityProvider(Protocol):
    """Resolves an :class:`Identity` for a given role."""

    def for_role(self, role: Role) -> Identity:
        """Return an identity authorised as ``role``."""
        ...

    def all_roles(self) -> tuple[Identity, ...]:
        """Return one identity per role (the role matrix)."""
        ...
