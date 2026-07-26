"""Deterministic seed credentials and catalog constants.

These passwords are demo-only fixtures for local development and CI. They must
never be reused outside this portfolio project.
"""

from __future__ import annotations

# nosec B105 - intentional demo-only seed password documented in README / .env.example.
DEMO_ONLY_SEED_PASSWORD = "ChangeMeDemoOnly!"

ADMIN_EMAIL = "admin@example.com"
OWNER_ONE_EMAIL = "owner1@example.com"
OWNER_TWO_EMAIL = "owner2@example.com"
CUSTOMER_ONE_EMAIL = "customer1@example.com"
CUSTOMER_TWO_EMAIL = "customer2@example.com"
DELIVERY_MANAGER_EMAIL = "delivery@example.com"

STORE_ONE_NAME = "Northwind Outfitters"
STORE_TWO_NAME = "Contoso Gadgets"
