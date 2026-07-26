Document Name: Advisory iter-01
Covered Elements: Feature and detection for iter-01 — CSV bulk product import and order-status state machine (A10)
Creation Date: 26/07/2026-17:30:00.000

# Security Advisory — A10 Mishandling of Exceptional Conditions

- **Iteration:** iter-01
- **OWASP Top 10:2025 (Web):** A10 Mishandling of Exceptional Conditions
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration (error handling) / exceptional-condition mishandling

## Summary

CSV bulk product import leaks Python stack traces when DEBUG=true, and the order-status state machine fails open on illegal transitions (e.g. delivered → pending).

## Detection

This flaw was proven by the failing detection test:

```
tests/security/test_a10_exceptional_conditions.py::test_debug_error_response_must_not_leak_stack_trace
tests/security/test_a10_exceptional_conditions.py::test_csv_import_exception_must_not_leak_stack_trace_markers
tests/security/test_a10_exceptional_conditions.py::test_csv_import_zero_division_must_not_leak_stack_trace_markers
tests/security/test_a10_exceptional_conditions.py::test_invalid_order_status_transition_must_be_rejected
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a10_exceptional_conditions.py | Detection suite asserting secure exceptional-condition handling; fails on vulnerable red-phase code. |

## Remediation

- Global unhandled-exception handler returns RFC 9457 `application/problem+json`
  with a generic detail string; FastAPI/Starlette debug error pages are disabled.
- Order-status transitions fail closed: illegal moves raise `ConflictError` (HTTP 409).
- Stack frames and exception type names are logged server-side only.
