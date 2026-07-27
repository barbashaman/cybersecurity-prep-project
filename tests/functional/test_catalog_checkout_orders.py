"""Functional persona-feature checks for catalog, checkout, shipping, and orders."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

pytestmark = [pytest.mark.functional, pytest.mark.api]


def _store_for_persona(stores: list[dict[str, Any]], store_id: int) -> dict[str, Any]:
    for store in stores:
        if store["id"] == store_id:
            return store
    raise AssertionError(f"Store id {store_id} not present in seeded catalog.")


def test_store_owner_cannot_read_other_store_catalog(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
    store_context: dict[str, Any],
) -> None:
    owner_store_id = principal_profiles["store_owner_secondary"]["store_id"]
    stores = store_context["stores"]
    other_store = next(store for store in stores if store["id"] != owner_store_id)

    response = client.get(
        f"{api_base_url}/api/v1/stores/{other_store['id']}/products",
        headers=auth_headers["store_owner_secondary"],
    )
    assert response.status_code == 403


def test_customer_can_read_own_catalog_and_place_order(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
) -> None:
    customer_store_id = principal_profiles["customer"]["store_id"]
    assert isinstance(customer_store_id, int)

    products_response = client.get(
        f"{api_base_url}/api/v1/stores/{customer_store_id}/products",
        headers=auth_headers["customer"],
    )
    assert products_response.status_code == 200, products_response.text
    products = products_response.json()
    assert isinstance(products, list) and products
    product_id = products[0]["id"]

    checkout_response = client.post(
        f"{api_base_url}/api/v1/stores/{customer_store_id}/orders/checkout",
        headers=auth_headers["customer"],
        json={
            "lines": [{"product_id": product_id, "quantity": 1}],
            "shipping_address": "Functional Test Street 100",
            "customer_phone": "+1-555-000-1000",
        },
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout_payload = checkout_response.json()
    assert checkout_payload["order"]["store_id"] == customer_store_id
    assert checkout_payload["total_cents"] >= 0


def test_delivery_manager_order_list_is_pii_anonymized(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
    principal_profiles: dict[str, dict[str, Any]],
) -> None:
    customer_store_id = principal_profiles["customer"]["store_id"]
    assert isinstance(customer_store_id, int)

    response = client.get(
        f"{api_base_url}/api/v1/stores/{customer_store_id}/orders",
        headers=auth_headers["delivery_manager"],
    )
    assert response.status_code == 200, response.text
    orders = response.json()
    assert isinstance(orders, list)
    if not orders:
        pytest.skip("No orders available for anonymization assertion.")
    payload = json.dumps(orders[0])
    assert "customer_email" not in payload
    assert "customer_full_name" not in payload
    assert "shipping_address" not in payload


def test_shipping_quote_denied_for_delivery_manager_but_allowed_for_customer(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
) -> None:
    quote_payload = {"destination_country": "PT", "parcel_weight_kg": 1.5}

    denied = client.post(
        f"{api_base_url}/api/v1/shipping/quote",
        headers=auth_headers["delivery_manager"],
        json=quote_payload,
    )
    assert denied.status_code == 403

    allowed = client.post(
        f"{api_base_url}/api/v1/shipping/quote",
        headers=auth_headers["customer"],
        json=quote_payload,
    )
    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert body["currency"] == "EUR"
    assert body["amount_cents"] > 0
