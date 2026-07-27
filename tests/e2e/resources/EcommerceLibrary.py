"""Robot Framework keyword library for persona-driven E2E journeys.

Uses httpx only (already in the test extras) so the suite stays lockfile-stable.
Targets a running seeded stack via ``TOOLKIT_BASE_URL`` / ``WEB_BASE_URL``.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, cast

import httpx
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn  # type: ignore[import-untyped]

from database.seeding.constants import (
    ADMIN_EMAIL,
    CUSTOMER_ONE_EMAIL,
    DELIVERY_MANAGER_EMAIL,
    DEMO_ONLY_SEED_PASSWORD,
    OWNER_ONE_EMAIL,
    OWNER_TWO_EMAIL,
)

_PERSONA_EMAILS: dict[str, str] = {
    "admin": ADMIN_EMAIL,
    "store_owner_primary": OWNER_ONE_EMAIL,
    "store_owner_secondary": OWNER_TWO_EMAIL,
    "customer": CUSTOMER_ONE_EMAIL,
    "delivery_manager": DELIVERY_MANAGER_EMAIL,
}


@library(scope="GLOBAL", auto_keywords=False)
class EcommerceLibrary:
    """HTTP keywords for API + Jinja web E2E flows."""

    def __init__(self) -> None:
        api_base = os.environ.get("TOOLKIT_BASE_URL") or os.environ.get("API_BASE_URL")
        self.api_base_url = (api_base or "http://localhost:8000").rstrip("/")
        self.web_base_url = (os.environ.get("WEB_BASE_URL") or "http://localhost:8080").rstrip("/")
        self._api = httpx.Client(timeout=10.0, follow_redirects=False)
        # Web sessions use signed cookies; follow redirects so login lands on dashboard.
        self._web = httpx.Client(timeout=10.0, follow_redirects=True)
        self._tokens: dict[str, str] = {}
        self._last_api: httpx.Response | None = None
        self._last_web: httpx.Response | None = None

    # ------------------------------------------------------------------ setup
    @keyword("Stack Must Be Healthy")
    def stack_must_be_healthy(self) -> None:
        """Skip the suite when API or web health endpoints are unreachable."""
        if not self._is_healthy(f"{self.api_base_url}/health"):
            BuiltIn().skip(
                f"API not healthy at {self.api_base_url}/health; "
                "set TOOLKIT_BASE_URL against a seeded stack."
            )
        if not self._is_healthy(f"{self.web_base_url}/health"):
            BuiltIn().skip(
                f"Web not healthy at {self.web_base_url}/health; "
                "set WEB_BASE_URL against a seeded stack."
            )

    def _is_healthy(self, url: str) -> bool:
        try:
            response = httpx.get(url, timeout=2.0)
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        payload = response.json()
        return isinstance(payload, dict) and payload.get("status") == "ok"

    # ------------------------------------------------------------------- auth
    @keyword("Login As Persona")
    def login_as_persona(self, persona: str) -> str:
        email = _PERSONA_EMAILS[persona]
        response = self._api.post(
            f"{self.api_base_url}/api/v1/auth/login",
            json={"email": email, "password": DEMO_ONLY_SEED_PASSWORD},
        )
        self._last_api = response
        if response.status_code != 200:
            raise AssertionError(
                f"Login failed for {persona}: {response.status_code} {response.text}"
            )
        token = response.json()["access_token"]
        assert isinstance(token, str) and token
        self._tokens[persona] = token
        return token

    @keyword("Auth Headers For")
    def auth_headers_for(self, persona: str) -> dict[str, str]:
        token = self._tokens.get(persona)
        if not token:
            token = self.login_as_persona(persona)
        return {"Authorization": f"Bearer {token}"}

    @keyword("Get Current User Profile")
    def get_current_user_profile(self, persona: str) -> dict[str, Any]:
        response = self._api.get(
            f"{self.api_base_url}/api/v1/auth/me",
            headers=self.auth_headers_for(persona),
        )
        self._last_api = response
        self.status_should_be(200)
        body = response.json()
        assert isinstance(body, dict)
        return body

    # -------------------------------------------------------------------- API
    @keyword("Api Get")
    def api_get(self, path: str, persona: str | None = None) -> Any:
        headers = self.auth_headers_for(persona) if persona else {}
        self._last_api = self._api.get(f"{self.api_base_url}{path}", headers=headers)
        return self._json_or_text(self._last_api)

    @keyword("Api Post")
    def api_post(self, path: str, persona: str, body: Any) -> Any:
        payload = body if isinstance(body, dict | list) else json.loads(str(body))
        self._last_api = self._api.post(
            f"{self.api_base_url}{path}",
            headers=self.auth_headers_for(persona),
            json=payload,
        )
        return self._json_or_text(self._last_api)

    @keyword("Api Patch")
    def api_patch(self, path: str, persona: str, body: Any) -> Any:
        payload = body if isinstance(body, dict | list) else json.loads(str(body))
        self._last_api = self._api.patch(
            f"{self.api_base_url}{path}",
            headers=self.auth_headers_for(persona),
            json=payload,
        )
        return self._json_or_text(self._last_api)

    @keyword("Last Api Status Should Be")
    def status_should_be(self, expected: int | str) -> None:
        assert self._last_api is not None, "No API response captured yet."
        expected_code = int(expected)
        assert self._last_api.status_code == expected_code, (
            f"Expected status {expected_code}, got {self._last_api.status_code}: "
            f"{self._last_api.text}"
        )

    @keyword("Last Api Body Should Not Contain")
    def last_api_body_should_not_contain(self, fragment: str) -> None:
        assert self._last_api is not None, "No API response captured yet."
        assert (
            fragment not in self._last_api.text
        ), f"Response unexpectedly contained {fragment!r}: {self._last_api.text}"

    @keyword("List Stores For Persona")
    def list_stores_for_persona(self, persona: str) -> list[dict[str, Any]]:
        body = self.api_get("/api/v1/stores", persona)
        self.status_should_be(200)
        assert isinstance(body, list)
        return body

    @keyword("List Products For Store")
    def list_products_for_store(self, persona: str, store_id: int | str) -> list[dict[str, Any]]:
        body = self.api_get(f"/api/v1/stores/{int(store_id)}/products", persona)
        return body if isinstance(body, list) else []

    @keyword("Find In Stock Product")
    def find_in_stock_product(self, persona: str, store_id: int | str) -> dict[str, Any]:
        """Return an in-stock catalog item, creating one when the shelf is empty."""
        products = self.list_products_for_store(persona, store_id)
        self.status_should_be(200)
        for product in products:
            if int(product.get("stock_quantity", 0)) > 0 and product.get("is_active", True):
                return cast(dict[str, Any], product)

        owner_persona = "store_owner_primary"
        owner_profile = self.get_current_user_profile(owner_persona)
        if int(owner_profile.get("store_id") or -1) != int(store_id):
            owner_persona = "admin"
        created = self.create_product_for_owner(owner_persona, store_id)
        return cast(dict[str, Any], created)

    @keyword("Checkout Product For Customer")
    def checkout_product_for_customer(
        self,
        store_id: int | str,
        product_id: int | str,
        quantity: int | str = 1,
    ) -> dict[str, Any]:
        body = self.api_post(
            f"/api/v1/stores/{int(store_id)}/orders/checkout",
            "customer",
            {
                "lines": [{"product_id": int(product_id), "quantity": int(quantity)}],
                "shipping_address": f"E2E Purchase Way {uuid.uuid4().hex[:8]}",
                "customer_phone": "+1-555-0600",
            },
        )
        self.status_should_be(201)
        assert isinstance(body, dict)
        return cast(dict[str, Any], body)

    @keyword("Create Product For Owner")
    def create_product_for_owner(
        self,
        persona: str,
        store_id: int | str,
        name: str | None = None,
    ) -> dict[str, Any]:
        product_name = name or f"E2E Widget {uuid.uuid4().hex[:8]}"
        body = self.api_post(
            f"/api/v1/stores/{int(store_id)}/products",
            persona,
            {
                "name": product_name,
                "description": "e2e catalog item",
                "price_cents": 1500,
                "stock_quantity": 25,
                "is_active": True,
            },
        )
        self.status_should_be(201)
        assert isinstance(body, dict)
        return cast(dict[str, Any], body)

    @keyword("Update Order Status")
    def update_order_status(self, persona: str, order_id: int | str, status_value: str) -> Any:
        body = self.api_patch(
            f"/api/v1/orders/{int(order_id)}/status",
            persona,
            {"status": status_value},
        )
        return body

    @keyword("Get Shipping Quote")
    def get_shipping_quote(self, persona: str) -> Any:
        return self.api_post(
            "/api/v1/shipping/quote",
            persona,
            {"destination_country": "PT", "parcel_weight_kg": 1.5},
        )

    @keyword("Get Store Revenue")
    def get_store_revenue(self, persona: str, store_public_id: str) -> Any:
        return self.api_get(f"/api/v1/stores/{store_public_id}/revenue", persona)

    @keyword("Create Store As Admin")
    def create_store_as_admin(self, name: str | None = None) -> dict[str, Any]:
        store_name = name or f"E2E Store {uuid.uuid4().hex[:8]}"
        body = self.api_post("/api/v1/stores", "admin", {"name": store_name, "owner_user_id": None})
        self.status_should_be(201)
        assert isinstance(body, dict)
        return body

    # -------------------------------------------------------------------- web
    @keyword("Web Login As Persona")
    def web_login_as_persona(self, persona: str) -> str:
        """Authenticate via the Jinja login form and land on the dashboard.

        The web tier sets ``Secure`` session cookies (A04). Lab stacks often
        serve plain HTTP, so cookies are force-copied into the client jar.
        """
        email = _PERSONA_EMAILS[persona]
        self._web.cookies.clear()
        login_response = self._web.post(
            f"{self.web_base_url}/login",
            data={"email": email, "password": DEMO_ONLY_SEED_PASSWORD},
            follow_redirects=False,
        )
        if login_response.status_code not in {302, 303}:
            self._last_web = login_response
            raise AssertionError(
                f"Web login failed for {persona}: {login_response.status_code} "
                f"{login_response.text[:500]}"
            )
        for name, value in login_response.cookies.items():
            self._web.cookies.set(name, value)
        response = self._web.get(f"{self.web_base_url}/dashboard")
        self._last_web = response
        if response.status_code != 200:
            raise AssertionError(
                f"Web dashboard failed for {persona}: {response.status_code} "
                f"{response.text[:500]}"
            )
        assert "Stores" in response.text, f"Web login did not reach dashboard for {persona}"
        return response.text

    @keyword("Web Open Path")
    def web_open_path(self, path: str) -> str:
        response = self._web.get(f"{self.web_base_url}{path}")
        self._last_web = response
        return response.text

    @keyword("Last Web Status Should Be")
    def last_web_status_should_be(self, expected: int | str) -> None:
        assert self._last_web is not None, "No web response captured yet."
        expected_code = int(expected)
        assert self._last_web.status_code == expected_code, (
            f"Expected web status {expected_code}, got {self._last_web.status_code}: "
            f"{self._last_web.text[:500]}"
        )

    @keyword("Last Web Body Should Contain")
    def last_web_body_should_contain(self, fragment: str) -> None:
        assert self._last_web is not None, "No web response captured yet."
        assert (
            fragment in self._last_web.text
        ), f"Web body missing {fragment!r}. Snippet: {self._last_web.text[:800]}"

    @keyword("Last Web Body Should Not Contain")
    def last_web_body_should_not_contain(self, fragment: str) -> None:
        assert self._last_web is not None, "No web response captured yet."
        assert fragment not in self._last_web.text, f"Web body unexpectedly contained {fragment!r}."

    @keyword("Last Web Header Should Match")
    def last_web_header_should_match(self, header_name: str, pattern: str) -> None:
        assert self._last_web is not None, "No web response captured yet."
        value = self._last_web.headers.get(header_name)
        assert value is not None, f"Missing response header {header_name!r}"
        assert re.search(
            pattern, value, flags=re.IGNORECASE
        ), f"Header {header_name!r}={value!r} did not match {pattern!r}"

    @keyword("Capture Web Login Set Cookie")
    def capture_web_login_set_cookie(self, persona: str) -> str:
        """Login without following redirects so Set-Cookie can be inspected."""
        email = _PERSONA_EMAILS[persona]
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.post(
                f"{self.web_base_url}/login",
                data={"email": email, "password": DEMO_ONLY_SEED_PASSWORD},
            )
        self._last_web = response
        cookie = response.headers.get("set-cookie", "")
        assert cookie, f"Expected Set-Cookie on web login, got status {response.status_code}"
        return cast(str, cookie)

    # ---------------------------------------------------------------- helpers
    def _json_or_text(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def close(self) -> None:
        self._api.close()
        self._web.close()
