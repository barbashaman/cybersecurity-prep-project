"""Infrastructure adapters for shipping-rate integrations."""

from __future__ import annotations


class MockShippingRateProvider:
    """Deterministic mock provider used for iteration demos and tests."""

    def fetch_quote(
        self, *, destination_country: str, parcel_weight_kg: float
    ) -> dict[str, object]:
        base = 7.5 if destination_country == "PT" else 9.0
        weight_surcharge = max(0.0, parcel_weight_kg - 1.0) * 1.75
        return {
            "carrier": "Acme Logistics",
            "service_level": "standard",
            "currency": "EUR",
            "amount": round(base + weight_surcharge, 2),
        }
