Document Name: Advisory iter-08
Covered Elements: Feature and detection for iter-08 — shipping-rate integration trust hardening (A03)
Creation Date: 27/07/2026-10:48:00.000

# Security Advisory — A03 Software Supply Chain Failures

- **Iteration:** iter-08
- **OWASP Top 10:2025 (Web):** A03 Software Supply Chain Failures
- **OWASP API Security Top 10 cross-reference:** API10:2023 Unsafe Consumption of APIs

## Summary

The shipping quote integration previously trusted third-party responses without strict schema controls. This enabled schema drift, unsafe field types, and poisoned values to enter downstream order calculations.

## Detection

```
tests/security/test_a03_supply_chain_failures.py::test_shipping_quote_must_reject_schema_drift_and_untrusted_fields
tests/security/test_a03_supply_chain_failures.py::test_shipping_quote_must_sanitize_and_normalize_trusted_payload
```

## Remediation

- Introduced `GetShippingQuote` to enforce an explicit upstream contract.
- Rejected responses with unknown/missing keys or wrong types.
- Sanitized provider text fields and normalized ISO-like currency + bounded amount parsing.
