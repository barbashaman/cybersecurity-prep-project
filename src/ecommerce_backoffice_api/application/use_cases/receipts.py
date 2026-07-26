"""Purchase receipt store/load use cases (iter-03 A08 — remediated).

Receipts are persisted as UTF-8 JSON only. Pickle protocol magic and non-JSON
blobs are rejected on load. A SHA-256 checksum of the canonical JSON is
verified when a ``checksum_sha256`` field is present in the document.
"""

from __future__ import annotations

import hashlib
import json

from ecommerce_backoffice_api.application.ports.repositories import (
    OrderRepository,
    ReceiptRepository,
)
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import OrderReceipt, User
from ecommerce_backoffice_api.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)

_PICKLE_PROTOCOL_MAGIC = b"\x80"
_CHECKSUM_FIELD = "checksum_sha256"


def _canonical_payload_json(receipt_payload: dict[str, object]) -> str:
    body = {key: value for key, value in receipt_payload.items() if key != _CHECKSUM_FIELD}
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def _build_receipt_blob(receipt_payload: dict[str, object]) -> bytes:
    canonical = _canonical_payload_json(receipt_payload)
    checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    document = json.loads(canonical)
    document[_CHECKSUM_FIELD] = checksum
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_receipt_blob(payload_blob: bytes) -> dict[str, object]:
    if payload_blob.startswith(_PICKLE_PROTOCOL_MAGIC):
        raise ConflictError("Receipt payload must be JSON; pickle blobs are rejected.")
    try:
        text = payload_blob.decode("utf-8")
        loaded = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConflictError("Receipt payload must be valid JSON.") from error
    if not isinstance(loaded, dict):
        raise ConflictError("Receipt payload must be a JSON object.")
    if _CHECKSUM_FIELD in loaded:
        provided = loaded[_CHECKSUM_FIELD]
        if not isinstance(provided, str):
            raise ConflictError("Receipt checksum is malformed.")
        expected = hashlib.sha256(_canonical_payload_json(loaded).encode("utf-8")).hexdigest()
        if not _constant_time_equals(expected, provided):
            raise ConflictError("Receipt checksum mismatch.")
    return {str(key): value for key, value in loaded.items() if key != _CHECKSUM_FIELD}


def _constant_time_equals(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    result = 0
    for left_char, right_char in zip(left, right, strict=True):
        result |= ord(left_char) ^ ord(right_char)
    return result == 0


class StoreOrderReceipt:
    """Persist a purchase receipt payload for an order."""

    def __init__(
        self,
        receipt_repository: ReceiptRepository,
        order_repository: OrderRepository,
    ) -> None:
        self._receipt_repository = receipt_repository
        self._order_repository = order_repository

    def execute(
        self,
        *,
        actor: User,
        order_id: int,
        receipt_payload: dict[str, object],
    ) -> OrderReceipt:
        order = self._order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        if not authorization.can_manage_order_receipt(actor, order):
            raise AuthorizationError("Not permitted to store a receipt for this order.")
        payload_blob = _build_receipt_blob(receipt_payload)
        return self._receipt_repository.save(
            OrderReceipt(order_id=order_id, payload_blob=payload_blob)
        )


class LoadOrderReceipt:
    """Load and deserialize a purchase receipt for an order."""

    def __init__(
        self,
        receipt_repository: ReceiptRepository,
        order_repository: OrderRepository,
    ) -> None:
        self._receipt_repository = receipt_repository
        self._order_repository = order_repository

    def execute(self, *, actor: User, order_id: int) -> dict[str, object]:
        order = self._order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        if not authorization.can_manage_order_receipt(actor, order):
            raise AuthorizationError("Not permitted to load a receipt for this order.")
        receipt = self._receipt_repository.get_for_order(order_id)
        if receipt is None:
            raise NotFoundError(f"Receipt for order {order_id} was not found.")
        return _parse_receipt_blob(receipt.payload_blob)
