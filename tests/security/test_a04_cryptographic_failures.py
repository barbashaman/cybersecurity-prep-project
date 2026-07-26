"""Detection tests for OWASP A04 — Cryptographic Failures (iter-07).

These tests assert *secure* behaviour:
- password hashes must use a strong KDF (Argon2 / bcrypt), not MD5
- sensitive PII at rest must not be stored as plaintext
- session cookies must include the ``Secure`` flag (and ideally ``HttpOnly``)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.sessions import SessionMiddleware
from starlette.testclient import TestClient

from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.infrastructure.persistence.models import (
    Base,
    OrderModel,
    StoreModel,
    UserModel,
)
from ecommerce_backoffice_api.infrastructure.security.password_hasher import (
    build_password_hasher,
)
from ecommerce_backoffice_web.main import create_app
from tests.toolkit.payloads.builders import plaintext_customer_phone_sample

pytestmark = pytest.mark.security

_MD5_HEX_RE = re.compile(r"^[0-9a-f]{32}$")
_STRONG_PASSWORD_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$", "$argon2")


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_password_hashes_must_use_strong_kdf_not_md5() -> None:
    """Secure: production hasher must emit Argon2/bcrypt-style digests, not MD5."""
    hasher = build_password_hasher()
    digest = hasher.hash_password("Correct-Horse-Battery-Staple-9!")

    assert not _MD5_HEX_RE.fullmatch(
        digest
    ), "Password digest looks like unsalted MD5 hex; use Argon2id or bcrypt."
    assert digest.startswith(
        _STRONG_PASSWORD_HASH_PREFIXES
    ), f"Expected Argon2/bcrypt hash prefix, got {digest[:12]!r}."


def test_sensitive_pii_at_rest_must_not_be_plaintext() -> None:
    """Secure: customer phone ciphertext at rest; ORM still decrypts for app use."""
    phone = plaintext_customer_phone_sample()
    session = _session()
    try:
        store = StoreModel(name="Northwind")
        session.add(store)
        session.flush()
        customer = UserModel(
            email="customer@example.test",
            password_hash="unused",
            role=UserRole.CUSTOMER.value,
            full_name="Casey Customer",
            store_id=store.id,
        )
        session.add(customer)
        session.flush()

        order = OrderModel(
            store_id=store.id,
            customer_user_id=customer.id,
            status=OrderStatus.PENDING.value,
            customer_email=customer.email,
            customer_full_name=customer.full_name,
            shipping_address="12 Pine Street",
            customer_phone=phone,
        )
        session.add(order)
        session.commit()

        # Bypass TypeDecorator decrypt: assert the on-disk column is not cleartext.
        raw_at_rest = session.execute(
            text("SELECT customer_phone FROM orders WHERE id = :id"),
            {"id": order.id},
        ).scalar_one()
        assert raw_at_rest != phone, (
            "Sensitive PII (customer_phone) is stored in plaintext at rest; "
            "encrypt with AES-GCM/Fernet and manage keys via secret management."
        )

        session.expire_all()
        loaded = session.get(OrderModel, order.id)
        assert loaded is not None
        assert loaded.customer_phone == phone
    finally:
        session.close()


def test_session_cookies_must_include_secure_and_httponly() -> None:
    """Secure: web session cookie must set Secure (and HttpOnly)."""
    app = create_app()
    session_options = _session_middleware_options(app)
    assert (
        session_options.get("https_only") is True
    ), "SessionMiddleware must set https_only=True so Set-Cookie includes Secure."

    with patch(
        "ecommerce_backoffice_web.api_client.ApiClient.login",
        return_value={"access_token": "demo-token", "role": "admin"},
    ):
        # HTTPS base URL so Secure cookies are emitted and visible to the client.
        client = TestClient(app, base_url="https://testserver")
        response = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "x"},
            follow_redirects=False,
        )

    set_cookie_headers = [
        value for value in response.headers.get_list("set-cookie") if "session=" in value.lower()
    ]
    assert set_cookie_headers, "Expected a session Set-Cookie after successful login."
    for cookie in set_cookie_headers:
        lowered = cookie.lower()
        assert "secure" in lowered, f"Session cookie missing Secure flag: {cookie}"
        assert "httponly" in lowered, f"Session cookie missing HttpOnly flag: {cookie}"


def _session_middleware_options(app: Any) -> dict[str, Any]:
    for middleware in app.user_middleware:
        if middleware.cls is SessionMiddleware:
            return dict(middleware.kwargs)
    pytest.fail("SessionMiddleware is not registered on the web app.")
