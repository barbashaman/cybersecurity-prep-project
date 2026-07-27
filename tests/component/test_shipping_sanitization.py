"""Component tests for shipping quote sanitization and persona access."""

from __future__ import annotations

import pytest
from tests.component.factories import make_user

from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, ConflictError

pytestmark = pytest.mark.component


class _TrustedProvider:
    def fetch_quote(
        self, *, destination_country: str, parcel_weight_kg: float
    ) -> dict[str, object]:
        del destination_country, parcel_weight_kg
        return {
            "carrier": "Acme Logistics",
            "service_level": "express",
            "currency": "eur",
            "amount": "12.90",
        }


class _PoisonedProvider:
    def fetch_quote(
        self, *, destination_country: str, parcel_weight_kg: float
    ) -> dict[str, object]:
        del destination_country, parcel_weight_kg
        return {
            "carrier": "<script>alert(1)</script>",
            "service_level": {"name": "overnight"},
            "currency": "EURO",
            "amount": "-3.5",
            "debug_payload": "unexpected",
        }


def test_shipping_quote_denied_for_delivery_manager() -> None:
    use_case = GetShippingQuote(_TrustedProvider())
    delivery = make_user(user_id=50, role=UserRole.DELIVERY_MANAGER, store_id=None)
    with pytest.raises(AuthorizationError):
        use_case.execute(actor=delivery, destination_country="PT", parcel_weight_kg=1.0)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.STORE_OWNER, UserRole.CUSTOMER])
def test_shipping_quote_allowed_and_normalized_for_permitted_roles(role: UserRole) -> None:
    use_case = GetShippingQuote(_TrustedProvider())
    actor = make_user(user_id=1, role=role, store_id=1 if role is not UserRole.ADMIN else None)
    result = use_case.execute(actor=actor, destination_country="pt", parcel_weight_kg=1.2)
    assert result.carrier == "Acme Logistics"
    assert result.service_level == "express"
    assert result.currency == "EUR"
    assert result.amount_cents == 1290


def test_shipping_quote_rejects_schema_drift_and_untrusted_fields() -> None:
    use_case = GetShippingQuote(_PoisonedProvider())
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    with pytest.raises(ConflictError):
        use_case.execute(actor=customer, destination_country="PT", parcel_weight_kg=1.0)
