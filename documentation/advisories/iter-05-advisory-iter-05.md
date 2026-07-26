Document Name: Advisory iter-05 (stub)
Covered Elements: Feature and detection for iter-05 — mock credits + coupons checkout (A06)
Creation Date: 26/07/2026-18:15:00.000

# Security Advisory — A06 Insecure Design

- **Iteration:** iter-05
- **OWASP Top 10:2025 (Web):** A06 Insecure Design
- **OWASP API Security Top 10 cross-reference:** API6:2023 Unrestricted Access to Sensitive Business Flows (coupon abuse, inventory integrity, missing business invariants)
- **Status:** Red-phase stub (detection failing; remediation not yet applied)

## Summary

Checkout allows reusable coupons, negative line quantities, and race-condition stock overselling because business invariants, redemption tracking, idempotency keys, and database constraints are missing.

## Detection

This flaw was proven by the failing detection tests:

```
tests/security/test_a06_insecure_design.py::test_coupon_must_not_be_reusable_after_redemption
tests/security/test_a06_insecure_design.py::test_checkout_must_reject_negative_quantity
tests/security/test_a06_insecure_design.py::test_checkout_must_reject_ordering_beyond_stock
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a06_insecure_design.py | Detection suite asserting single-use coupons, positive quantities, and atomic stock constraints; fails on vulnerable red-phase checkout. |

## Planned remediation (not yet applied)

- Threat-model checkout as a sensitive business flow.
- Enforce domain invariants: `quantity > 0`, `stock >= quantity`, single-use coupon redemption.
- Honour client idempotency keys for checkout retries.
- Persist unique redemption rows and DB `CHECK` / atomic stock constraints.
