"""Shared fixtures for functional persona/feature coverage.

These tests target a running seeded API and are skipped when the API endpoint
is not configured or unhealthy.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from database.seeding.constants import (
    ADMIN_EMAIL,
    CUSTOMER_ONE_EMAIL,
    DELIVERY_MANAGER_EMAIL,
    DEMO_ONLY_SEED_PASSWORD,
    OWNER_ONE_EMAIL,
    OWNER_TWO_EMAIL,
)


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


@pytest.fixture(scope="session")
def api_base_url() -> str:
    base_url = _base_url()
    if not base_url or not _api_is_healthy(base_url):
        pytest.skip("Functional API not reachable; set TOOLKIT_BASE_URL against a seeded stack.")
    return base_url.rstrip("/")


@pytest.fixture(scope="session")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=8.0) as http_client:
        yield http_client


@pytest.fixture(scope="session")
def persona_emails() -> dict[str, str]:
    return {
        "admin": ADMIN_EMAIL,
        "store_owner_primary": OWNER_ONE_EMAIL,
        "store_owner_secondary": OWNER_TWO_EMAIL,
        "customer": CUSTOMER_ONE_EMAIL,
        "delivery_manager": DELIVERY_MANAGER_EMAIL,
    }


def _login(client: httpx.Client, api_base_url: str, *, email: str) -> str:
    response = client.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": DEMO_ONLY_SEED_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert isinstance(token, str) and token
    return token


@pytest.fixture(scope="session")
def tokens(
    client: httpx.Client,
    api_base_url: str,
    persona_emails: dict[str, str],
) -> dict[str, str]:
    return {
        persona: _login(client, api_base_url, email=email)
        for persona, email in persona_emails.items()
    }


@pytest.fixture(scope="session")
def auth_headers(tokens: dict[str, str]) -> dict[str, dict[str, str]]:
    return {
        persona: {"Authorization": f"Bearer {token}"}
        for persona, token in tokens.items()
    }


@pytest.fixture(scope="session")
def principal_profiles(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for persona, headers in auth_headers.items():
        response = client.get(f"{api_base_url}/api/v1/auth/me", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert isinstance(body, dict)
        profiles[persona] = body
    return profiles


@pytest.fixture(scope="session")
def store_context(
    client: httpx.Client,
    api_base_url: str,
    auth_headers: dict[str, dict[str, str]],
) -> dict[str, Any]:
    response = client.get(f"{api_base_url}/api/v1/stores", headers=auth_headers["admin"])
    assert response.status_code == 200, response.text
    stores = response.json()
    assert isinstance(stores, list)
    assert len(stores) >= 2, "Expected at least two seeded stores for cross-tenant scenarios."
    for store in stores:
        assert isinstance(store, dict)
        assert "id" in store and "public_id" in store
    return {"stores": stores}
