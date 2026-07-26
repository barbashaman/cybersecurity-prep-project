"""Purchase receipt store/load use cases (iter-03 A08 vehicle).

VULNERABLE (red phase): receipt payloads are serialized and loaded with
``pickle``, which deserializes untrusted data and enables integrity failures
(and potential code execution).

Remediation plan (not implemented here): persist JSON only, reject pickle
protocol magic, and verify a checksum (or HMAC) over the receipt manifest before
accepting the payload.
"""

from __future__ import annotations

import pickle  # nosec B403

from ecommerce_backoffice_api.application.ports.repositories import (
    OrderRepository,
    ReceiptRepository,
)
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import OrderReceipt, User
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError


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
        # Deliberately uses pickle instead of JSON (A08 software/data integrity).
        # Intentional A08 red-phase integrity failure: pickle instead of JSON.
        payload_blob = pickle.dumps(receipt_payload)  # nosec B301
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
        # Intentional A08 red-phase integrity failure: untrusted pickle.loads.
        loaded = pickle.loads(receipt.payload_blob)  # noqa: S301  # nosec B301
        if not isinstance(loaded, dict):
            raise NotFoundError(f"Receipt for order {order_id} was not found.")
        return {str(key): value for key, value in loaded.items()}
