"""HTTP client used by the Jinja2 web tier to call the API.

The web package must not import ``ecommerce_backoffice_api``; all data access
goes through ``API_BASE_URL``.
"""

from __future__ import annotations

from typing import Any

import httpx


class ApiClientError(Exception):
    """Raised when the upstream API returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    """Thin httpx wrapper for server-side calls from the web tier."""

    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _headers(self, access_token: str | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        access_token: str | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.request(
                method,
                url,
                headers=self._headers(access_token),
                json=json_body,
            )
        if response.status_code >= 400:
            detail: str
            try:
                payload = response.json()
                raw_detail = payload.get("detail", response.text)
                detail = raw_detail if isinstance(raw_detail, str) else str(raw_detail)
            except ValueError:
                detail = response.text
            raise ApiClientError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def login(self, email: str, password: str) -> dict[str, Any]:
        result = self.request(
            "POST",
            "/api/v1/auth/login",
            json_body={"email": email, "password": password},
        )
        if not isinstance(result, dict):
            raise ApiClientError(500, "Unexpected login response shape.")
        return result

    def list_stores(self, access_token: str) -> list[dict[str, Any]]:
        result = self.request("GET", "/api/v1/stores", access_token=access_token)
        if not isinstance(result, list):
            raise ApiClientError(500, "Unexpected stores response shape.")
        return result

    def get_store(self, access_token: str, store_id: int) -> dict[str, Any]:
        result = self.request("GET", f"/api/v1/stores/{store_id}", access_token=access_token)
        if not isinstance(result, dict):
            raise ApiClientError(500, "Unexpected store response shape.")
        return result

    def list_products(self, access_token: str, store_id: int) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            f"/api/v1/stores/{store_id}/products",
            access_token=access_token,
        )
        if not isinstance(result, list):
            raise ApiClientError(500, "Unexpected products response shape.")
        return result

    def list_orders(self, access_token: str, store_id: int) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            f"/api/v1/stores/{store_id}/orders",
            access_token=access_token,
        )
        if not isinstance(result, list):
            raise ApiClientError(500, "Unexpected orders response shape.")
        return result
