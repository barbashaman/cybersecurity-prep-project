"""Identity provider that obtains real JWTs via ``POST /api/v1/auth/login``."""

from __future__ import annotations

import json

from database.seeding.constants import (
    ADMIN_EMAIL,
    CUSTOMER_ONE_EMAIL,
    DELIVERY_MANAGER_EMAIL,
    DEMO_ONLY_SEED_PASSWORD,
    OWNER_ONE_EMAIL,
)
from tests.toolkit.clients.protocols import TransportClient
from tests.toolkit.identities.protocols import Identity, IdentityProvider
from tests.toolkit.identities.roles import Role

_ROLE_EMAILS: dict[Role, str] = {
    Role.ADMIN: ADMIN_EMAIL,
    Role.STORE_OWNER: OWNER_ONE_EMAIL,
    Role.CUSTOMER: CUSTOMER_ONE_EMAIL,
    Role.DELIVERY_MANAGER: DELIVERY_MANAGER_EMAIL,
}


class LoginIdentityProvider(IdentityProvider):
    """Resolve identities by logging in as the seeded account for each role."""

    def __init__(
        self,
        client: TransportClient,
        *,
        password: str = DEMO_ONLY_SEED_PASSWORD,
    ) -> None:
        self._client = client
        self._password = password

    def for_role(self, role: Role) -> Identity:
        email = _ROLE_EMAILS[role]
        response = self._client.request(
            "POST",
            "/api/v1/auth/login",
            headers={"content-type": "application/json"},
            body=json.dumps({"email": email, "password": self._password}),
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Login failed for role {role.value} ({email}): "
                f"HTTP {response.status_code} {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Login response was not a JSON object.")
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Login response did not include access_token.")
        return Identity(role=role, subject=email, token=token)

    def all_roles(self) -> tuple[Identity, ...]:
        return tuple(self.for_role(role) for role in Role)
