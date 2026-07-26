"""Optional API smoke tests against a running, seeded stack.

Skipped when ``TOOLKIT_BASE_URL`` is unset or the target ``/health`` is unhealthy.
Quality-gate CI stays offline; run these when compose is up.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest

from database.seeding.constants import ADMIN_EMAIL, DEMO_ONLY_SEED_PASSWORD, OWNER_TWO_EMAIL

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def _base_url() -> str | None:
    return os.environ.get("TOOLKIT_BASE_URL") or os.environ.get("API_BASE_URL")


def _api_is_healthy(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=2.0)
    except httpx.HTTPError:
        return False
    if response.status_code != 200:
        return False
    payload = response.json()
    return isinstance(payload, dict) and payload.get("status") == "ok"


@pytest.fixture(scope="module")
def api_base_url() -> str:
    base_url = _base_url()
    if not base_url or not _api_is_healthy(base_url):
        pytest.skip("API not reachable; set TOOLKIT_BASE_URL against a seeded stack.")
    return base_url.rstrip("/")


def _login(api_base_url: str, email: str) -> str:
    response = httpx.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": DEMO_ONLY_SEED_PASSWORD},
        timeout=5.0,
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert isinstance(token, str)
    return token


def test_admin_login_and_me(api_base_url: str) -> None:
    token = _login(api_base_url, ADMIN_EMAIL)
    response = httpx.get(
        f"{api_base_url}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_store_owner_cannot_read_other_store_catalog(api_base_url: str) -> None:
    token = _login(api_base_url, OWNER_TWO_EMAIL)
    # owner2 is bound to store 2; store 1 catalog must be forbidden.
    response = httpx.get(
        f"{api_base_url}/api/v1/stores/1/products",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    assert response.status_code == 403


def test_delivery_manager_order_omits_customer_pii(api_base_url: str) -> None:
    token = _login(api_base_url, "delivery@example.com")
    listed = httpx.get(
        f"{api_base_url}/api/v1/stores/1/orders",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    assert listed.status_code == 200, listed.text
    orders = listed.json()
    assert isinstance(orders, list)
    assert orders, "Expected seeded orders for store 1"
    payload = json.dumps(orders[0])
    assert "customer_email" not in payload
    assert "customer_full_name" not in payload
    assert "shipping_address" not in payload
    assert "status" in orders[0]
