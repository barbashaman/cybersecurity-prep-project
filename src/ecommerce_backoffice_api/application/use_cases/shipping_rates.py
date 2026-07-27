"""Shipping-rate integration hardening (iter-08 A03)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, ConflictError


class ShippingRateProvider(Protocol):
    """Port for upstream shipping-rate providers."""

    def fetch_quote(
        self,
        *,
        destination_country: str,
        parcel_weight_kg: float,
    ) -> dict[str, object]:
        """Return an upstream shipping quote payload."""
        ...


@dataclass(frozen=True, slots=True)
class ShippingQuoteView:
    """Sanitized quote returned to API consumers."""

    carrier: str
    service_level: str
    currency: str
    amount_cents: int


class GetShippingQuote:
    """Fetch and validate third-party shipping quotes."""

    def __init__(self, provider: ShippingRateProvider) -> None:
        self._provider = provider

    def execute(
        self,
        *,
        actor: User,
        destination_country: str,
        parcel_weight_kg: float,
    ) -> ShippingQuoteView:
        if actor.role not in {UserRole.ADMIN, UserRole.STORE_OWNER, UserRole.CUSTOMER}:
            raise AuthorizationError("Not permitted to read shipping quotes.")
        if parcel_weight_kg <= 0:
            raise ConflictError("Parcel weight must be positive.")

        upstream = self._provider.fetch_quote(
            destination_country=destination_country.strip().upper(),
            parcel_weight_kg=parcel_weight_kg,
        )
        return _validated_quote_from_upstream(upstream)


def _validated_quote_from_upstream(payload: dict[str, object]) -> ShippingQuoteView:
    required_keys = {"carrier", "service_level", "currency", "amount"}
    if set(payload.keys()) != required_keys:
        raise ConflictError("Shipping provider response schema is invalid.")

    carrier = _clean_text(payload["carrier"], field_name="carrier")
    service_level = _clean_text(payload["service_level"], field_name="service_level")
    currency = _clean_currency(payload["currency"])
    amount_cents = _clean_amount(payload["amount"])

    return ShippingQuoteView(
        carrier=carrier,
        service_level=service_level,
        currency=currency,
        amount_cents=amount_cents,
    )


def _clean_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConflictError(f"Shipping provider field '{field_name}' must be a string.")
    cleaned = "".join(char for char in value.strip() if char.isalnum() or char in {" ", "-", "_"})
    if not cleaned:
        raise ConflictError(f"Shipping provider field '{field_name}' is empty.")
    return cleaned[:64]


def _clean_currency(value: object) -> str:
    if not isinstance(value, str):
        raise ConflictError("Shipping provider field 'currency' must be a string.")
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ConflictError("Shipping provider currency must be ISO-4217-like (3 letters).")
    return currency


def _clean_amount(value: object) -> int:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ConflictError("Shipping provider field 'amount' must be numeric.") from error
    if parsed <= 0:
        raise ConflictError("Shipping provider amount must be positive.")
    amount_cents = int(parsed * 100)
    if amount_cents <= 0 or amount_cents > 2_000_000:
        raise ConflictError("Shipping provider amount is outside allowed bounds.")
    return amount_cents
