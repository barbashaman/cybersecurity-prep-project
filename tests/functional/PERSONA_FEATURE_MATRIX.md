# Functional Persona-Feature Matrix

This matrix tracks required functional coverage for core persona-feature paths.
Each row is validated by one or more tests in `tests/functional`.

| Persona | Auth (`/auth/me`) | Stores (`/stores`) | Catalog (`/stores/{id}/products`) | Checkout (`/stores/{id}/orders/checkout`) | Shipping (`/shipping/quote`) | Orders (`/stores/{id}/orders`) | Admin (`/admin/users`) | Coupons (`/coupons`) | Credits (`/credits/grant`) | Revenue (`/stores/{public_id}/revenue`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admin | allow | allow all | allow all | allow | allow | allow | allow | allow | allow | allow |
| store_owner_primary | allow | allow own scope | allow own scope | deny | allow | allow own scope | deny | allow own, deny foreign | deny | allow own, deny foreign |
| store_owner_secondary | allow | allow own scope | allow own, deny foreign | deny | allow | allow own scope | deny | allow own, deny foreign | deny | allow own, deny foreign |
| customer | allow | allow own scope | allow own scope | allow own scope | allow | allow own/customer scope | deny | deny | allow self, deny others by policy | deny |
| delivery_manager | allow | allow all | allow all | deny | deny | allow anonymized view | deny | deny | deny | allow |

## Traceability

- `test_auth_and_store_access.py`
  - persona role assertions
  - missing-token rejection
  - store visibility scope
  - admin-only store creation
- `test_catalog_checkout_orders.py`
  - cross-tenant catalog denial
  - customer checkout happy path
  - delivery-manager anonymized order projection
  - shipping allow/deny by role
- `test_admin_coupons_credits_revenue.py`
  - admin directory allow/deny
  - coupon tenant boundary enforcement
  - credit grant role restrictions
  - revenue tenant boundary enforcement
