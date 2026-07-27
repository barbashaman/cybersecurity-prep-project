Document Name: Advisory iter-10
Covered Elements: Feature and detection for iter-10 — cross-store revenue analytics access control (A01)
Creation Date: 27/07/2026-10:50:00.000

# Security Advisory — A01 Broken Access Control

- **Iteration:** iter-10
- **OWASP Top 10:2025 (Web):** A01 Broken Access Control
- **OWASP API Security Top 10 cross-reference:** API1:2023 Broken Object Level Authorization

## Summary

Cross-store revenue analytics is a high-value BOLA/IDOR target. Access must be constrained by centralized policy enforcement and object-level authorization, and externally exposed resource keys should avoid sequential identifiers.

## Detection

```
tests/security/test_a01_broken_access_control.py::test_cross_store_revenue_must_be_blocked_for_other_store_owner
tests/security/test_a01_broken_access_control.py::test_store_revenue_must_use_uuid_lookup_and_authorized_scope
```

## Remediation

- Added `GetStoreRevenue` with a centralized `RevenueAccessPolicy`.
- Enforced object-level authorization for store owners and admins only.
- Introduced `stores.public_id` UUIDv4 identifiers and analytics lookup by public UUID.
