"""Detection tests for OWASP A03 — Software Supply Chain Failures (iter-08)."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import ConflictError

pytestmark = pytest.mark.security


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


class _CompromisedProviderWithSchemaDrift:
    def fetch_quote(
        self, *, destination_country: str, parcel_weight_kg: float
    ) -> dict[str, object]:
        del destination_country, parcel_weight_kg
        return {
            "carrier": "<script>alert(1)</script>",
            "service_level": {"name": "overnight"},
            "currency": "EURO",
            "amount": "-3.5",
            "debug_payload": "unexpected key that should fail schema checks",
        }


def _customer() -> User:
    return User(
        id=101,
        email="customer@example.test",
        password_hash="unused",
        role=UserRole.CUSTOMER,
        full_name="Casey Customer",
        store_id=1,
    )


def test_shipping_quote_must_reject_schema_drift_and_untrusted_fields() -> None:
    # Threat category: OWASP A03 (Supply Chain / Software Integrity Failures).
    # Attack path: third-party shipping provider response drifts from trusted
    # schema and injects unsafe data.
    # Expected secure behavior: reject payload when structure/content violate integration contract.
    # Failure impact: poisoned downstream state, script injection vectors, and pricing manipulation.
    # Arrange
    use_case = GetShippingQuote(_CompromisedProviderWithSchemaDrift())

    # Act + Assert
    with pytest.raises(ConflictError):
        use_case.execute(
            actor=_customer(),
            destination_country="PT",
            parcel_weight_kg=1.2,
        )


def test_shipping_quote_must_sanitize_and_normalize_trusted_payload() -> None:
    # Threat category: OWASP A03 (Supply Chain / Software Integrity Failures).
    # Attack path: valid upstream payload still arrives with lowercase
    # country/currency input variants.
    # Expected secure behavior: normalize and sanitize trusted fields before returning to callers.
    # Failure impact: inconsistent contract surface can cascade into accounting/reporting defects.
    # Arrange
    use_case = GetShippingQuote(_TrustedProvider())

    # Act
    result = use_case.execute(
        actor=_customer(),
        destination_country="pt",
        parcel_weight_kg=1.2,
    )

    # Assert
    assert result.carrier == "Acme Logistics"
    assert result.service_level == "express"
    assert result.currency == "EUR"
    assert result.amount_cents == 1290
