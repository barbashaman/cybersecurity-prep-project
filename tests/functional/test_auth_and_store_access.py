"""Functional persona-feature checks for auth and store visibility."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

pytestmark = [pytest.mark.functional, pytest.mark.api]


@pytest.mark.parametrize(
    ("persona", "expected_role"),
    [
        ("admin", "admin"),
        ("store_owner_primary", "store_owner"),
        ("store_owner_secondary", "store_owner"),
        ("customer", "customer"),
        ("delivery_manager", "delivery_manager"),
    ],
)
def test_auth_me_returns_expected_persona_role(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    persona: str,
    expected_role: str,
) -> None:
    response = client.get(f"{api_base_url}/api/v1/auth/me", headers=auth_headers[persona])
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == expected_role
    assert isinstance(payload["email"], str) and payload["email"]


def test_missing_token_is_rejected_for_store_listing(
    client: httpx.Client,
    api_base_url: str,
) -> None:
    response = client.get(f"{api_base_url}/api/v1/stores")
    assert response.status_code == 401


def test_store_list_scope_matches_persona_policy(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
) -> None:
    admin_response = client.get(f"{api_base_url}/api/v1/stores", headers=auth_headers["admin"])
    owner_response = client.get(
        f"{api_base_url}/api/v1/stores",
        headers=auth_headers["store_owner_secondary"],
    )
    customer_response = client.get(
        f"{api_base_url}/api/v1/stores",
        headers=auth_headers["customer"],
    )
    delivery_response = client.get(
        f"{api_base_url}/api/v1/stores",
        headers=auth_headers["delivery_manager"],
    )

    assert admin_response.status_code == 200, admin_response.text
    assert owner_response.status_code == 200, owner_response.text
    assert customer_response.status_code == 200, customer_response.text
    assert delivery_response.status_code == 200, delivery_response.text

    admin_stores = admin_response.json()
    owner_stores = owner_response.json()
    customer_stores = customer_response.json()
    delivery_stores = delivery_response.json()

    assert isinstance(admin_stores, list)
    assert isinstance(owner_stores, list)
    assert isinstance(customer_stores, list)
    assert isinstance(delivery_stores, list)

    # Admin + delivery manager can enumerate all stores.
    assert len(admin_stores) >= 2
    assert len(delivery_stores) == len(admin_stores)
    # Store owner and customer are tenant-scoped.
    assert len(owner_stores) <= 1
    assert len(customer_stores) <= 1


def test_store_creation_is_admin_only(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
) -> None:
    owner_id = principal_profiles["store_owner_primary"]["id"]
    payload = {"name": "Functional Matrix Store", "owner_user_id": owner_id}

    denied = client.post(
        f"{api_base_url}/api/v1/stores",
        headers=auth_headers["store_owner_primary"],
        json=payload,
    )
    assert denied.status_code == 403

    allowed = client.post(
        f"{api_base_url}/api/v1/stores",
        headers=auth_headers["admin"],
        json=payload,
    )
    assert allowed.status_code == 201, allowed.text
