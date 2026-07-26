"""Detection tests for OWASP A08 — Software or Data Integrity Failures (iter-03).

These tests assert *secure* behaviour:
- theme uploads must reject unsigned / unverified artifacts (HMAC required)
- receipt persistence must be JSON-only (not pickle protocol)
- receipt load must reject pickle payloads (never ``pickle.loads`` untrusted blobs)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import json
import pickle

import pytest

from ecommerce_backoffice_api.application.use_cases.receipts import (
    LoadOrderReceipt,
    StoreOrderReceipt,
)
from ecommerce_backoffice_api.application.use_cases.themes import UploadStoreTheme
from ecommerce_backoffice_api.domain.entities import Order, OrderReceipt, Store, StoreTheme, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import ConflictError

pytestmark = pytest.mark.security


class _FakeStoreRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    def get_by_id(self, store_id: int) -> Store | None:
        return self._store if self._store.id == store_id else None

    def list_all(self) -> list[Store]:
        return [self._store]

    def add(self, store: Store) -> Store:
        return store


class _FakeThemeRepository:
    def __init__(self) -> None:
        self.themes: list[StoreTheme] = []
        self._next_id = 1

    def get_for_store(self, store_id: int) -> StoreTheme | None:
        for theme in self.themes:
            if theme.store_id == store_id:
                return theme
        return None

    def save(self, theme: StoreTheme) -> StoreTheme:
        theme.id = self._next_id
        self._next_id += 1
        self.themes = [existing for existing in self.themes if existing.store_id != theme.store_id]
        self.themes.append(theme)
        return theme


class _FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self._order = order

    def list_for_store(self, store_id: int) -> list[Order]:
        return [self._order] if self._order.store_id == store_id else []

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        if self._order.store_id == store_id and self._order.customer_user_id == customer_user_id:
            return [self._order]
        return []

    def get_by_id(self, order_id: int) -> Order | None:
        return self._order if self._order.id == order_id else None

    def add(self, order: Order) -> Order:
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        self._order.status = status
        return self._order


class _FakeReceiptRepository:
    def __init__(self) -> None:
        self.receipts: dict[int, OrderReceipt] = {}
        self._next_id = 1

    def get_for_order(self, order_id: int) -> OrderReceipt | None:
        return self.receipts.get(order_id)

    def save(self, receipt: OrderReceipt) -> OrderReceipt:
        receipt.id = self._next_id
        self._next_id += 1
        self.receipts[receipt.order_id] = receipt
        return receipt


def _admin() -> User:
    return User(
        id=1,
        email="admin@example.test",
        password_hash="unused",
        role=UserRole.ADMIN,
        full_name="Ada Admin",
        store_id=None,
    )


def _store() -> Store:
    return Store(id=1, name="Northwind Outfitters", owner_user_id=2)


def _order() -> Order:
    return Order(
        id=42,
        store_id=1,
        customer_user_id=10,
        status=OrderStatus.CONFIRMED,
        customer_email="customer1@example.test",
        customer_full_name="Casey Customer",
        shipping_address="1 Demo Way, Lisbon",
    )


def test_theme_upload_must_reject_unsigned_artifact() -> None:
    """Secure: theme uploads without a valid HMAC/signature must be rejected."""
    theme_repo = _FakeThemeRepository()
    use_case = UploadStoreTheme(theme_repo, _FakeStoreRepository(_store()))
    unsigned_artifact = b'{"primary_color":"#112233","extra_script":"alert(1)"}'

    with pytest.raises(ConflictError):
        use_case.execute(
            actor=_admin(),
            store_id=1,
            artifact_bytes=unsigned_artifact,
            signature_hex=None,
        )

    assert theme_repo.themes == [], "unsigned theme artifacts must not be persisted"


def test_theme_upload_must_reject_invalid_signature() -> None:
    """Secure: a present but invalid HMAC/signature must be rejected."""
    theme_repo = _FakeThemeRepository()
    use_case = UploadStoreTheme(theme_repo, _FakeStoreRepository(_store()))
    artifact = b'{"primary_color":"#abcdef"}'

    with pytest.raises(ConflictError):
        use_case.execute(
            actor=_admin(),
            store_id=1,
            artifact_bytes=artifact,
            signature_hex="deadbeef" * 8,
        )

    assert theme_repo.themes == [], "forged theme signatures must not be persisted"


def test_receipt_store_must_persist_json_not_pickle() -> None:
    """Secure: stored receipt bytes must be JSON (not pickle protocol)."""
    receipt_repo = _FakeReceiptRepository()
    use_case = StoreOrderReceipt(receipt_repo, _FakeOrderRepository(_order()))

    use_case.execute(
        actor=_admin(),
        order_id=42,
        receipt_payload={"total_cents": 1999, "currency": "EUR"},
    )

    blob = receipt_repo.receipts[42].payload_blob
    assert not blob.startswith(b"\x80"), "receipt blobs must not use pickle protocol magic"
    parsed = json.loads(blob.decode("utf-8"))
    assert parsed["total_cents"] == 1999
    assert parsed["currency"] == "EUR"


def test_receipt_load_must_reject_pickle_payload() -> None:
    """Secure: loading a receipt must reject pickle payloads (JSON-only + checksum)."""
    receipt_repo = _FakeReceiptRepository()
    pickle_blob = pickle.dumps({"total_cents": 1, "__exploit__": True})
    receipt_repo.receipts[42] = OrderReceipt(id=1, order_id=42, payload_blob=pickle_blob)
    use_case = LoadOrderReceipt(receipt_repo, _FakeOrderRepository(_order()))

    with pytest.raises(ConflictError):
        use_case.execute(actor=_admin(), order_id=42)
