"""Functional persona-feature checks for admin, coupons, credits, and revenue."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

pytestmark = [pytest.mark.functional, pytest.mark.api]


def _store_for_persona(stores: list[dict[str, Any]], store_id: int) -> dict[str, Any]:
    for store in stores:
        if store["id"] == store_id:
            return store
    raise AssertionError(f"Store id {store_id} not found in store list.")


def test_admin_directory_is_admin_only(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
) -> None:
    admin_response = client.get(f"{api_base_url}/api/v1/admin/users", headers=auth_headers["admin"])
    customer_response = client.get(
        f"{api_base_url}/api/v1/admin/users",
        headers=auth_headers["customer"],
    )

    assert admin_response.status_code == 200, admin_response.text
    users = admin_response.json()
    assert isinstance(users, list) and users
    assert customer_response.status_code == 403


def test_coupon_management_respects_tenant_scope(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
    store_context: dict[str, Any],
) -> None:
    stores = store_context["stores"]
    owner_store_id = principal_profiles["store_owner_secondary"]["store_id"]
    assert isinstance(owner_store_id, int)

    foreign_store = next(store for store in stores if store["id"] != owner_store_id)
    own_store = _store_for_persona(stores, owner_store_id)

    denied = client.post(
        f"{api_base_url}/api/v1/coupons",
        headers=auth_headers["store_owner_secondary"],
        json={
            "store_id": foreign_store["id"],
            "code": "FUNC-DENIED-10",
            "discount_percent": 10,
        },
    )
    assert denied.status_code == 403

    allowed = client.post(
        f"{api_base_url}/api/v1/coupons",
        headers=auth_headers["store_owner_secondary"],
        json={
            "store_id": own_store["id"],
            "code": "FUNC-ALLOW-10",
            "discount_percent": 10,
        },
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["store_id"] == own_store["id"]


def test_credit_grant_allowed_for_customer_self_and_denied_for_store_owner(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
) -> None:
    customer_id = principal_profiles["customer"]["id"]
    assert isinstance(customer_id, int)

    denied = client.post(
        f"{api_base_url}/api/v1/credits/grant",
        headers=auth_headers["store_owner_primary"],
        json={"user_id": customer_id, "amount_cents": 100},
    )
    assert denied.status_code == 403

    allowed = client.post(
        f"{api_base_url}/api/v1/credits/grant",
        headers=auth_headers["customer"],
        json={"user_id": customer_id, "amount_cents": 100},
    )
    assert allowed.status_code == 201, allowed.text
    body = allowed.json()
    assert body["user_id"] == customer_id
    assert body["balance_cents"] >= 100


def test_revenue_endpoint_enforces_owner_tenant_boundary(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
    store_context: dict[str, Any],
) -> None:
    stores = store_context["stores"]
    owner_primary_store_id = principal_profiles["store_owner_primary"]["store_id"]
    owner_secondary_store_id = principal_profiles["store_owner_secondary"]["store_id"]
    assert isinstance(owner_primary_store_id, int)
    assert isinstance(owner_secondary_store_id, int)

    own_store = _store_for_persona(stores, owner_primary_store_id)
    foreign_store = _store_for_persona(stores, owner_secondary_store_id)

    allowed = client.get(
        f"{api_base_url}/api/v1/stores/{own_store['public_id']}/revenue",
        headers=auth_headers["store_owner_primary"],
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["store_public_id"] == own_store["public_id"]

    denied = client.get(
        f"{api_base_url}/api/v1/stores/{foreign_store['public_id']}/revenue",
        headers=auth_headers["store_owner_primary"],
    )
    assert denied.status_code == 403
