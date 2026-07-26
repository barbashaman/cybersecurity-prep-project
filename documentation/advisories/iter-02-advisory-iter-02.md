Document Name: Advisory iter-02
Covered Elements: Admin audit trail persists successful admin actions but skips authorization failures, and plaintext application logs include bearer tokens plus PII (emails, names, shipping addresses).
Creation Date: 26/07/2026-16:47:15.749

# Security Advisory — A09 Security Logging and Alerting Failures

- **Iteration:** iter-02
- **OWASP Top 10:2025 (Web):** A09 Security Logging and Alerting Failures
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration (insufficient logging) / API security logging failures

## Summary

Admin audit trail persists successful admin actions but skips authorization failures, and plaintext application logs include bearer tokens plus PII (emails, names, shipping addresses).

## Detection

This flaw was proven by the failing detection test:

```
tests/security/test_a09_logging_alerting.py::test_authorization_failure_must_produce_audit_event
tests/security/test_a09_logging_alerting.py::test_list_users_authorization_failure_must_produce_audit_event
tests/security/test_a09_logging_alerting.py::test_sensitive_admin_logging_must_not_contain_bearer_tokens
tests/security/test_a09_logging_alerting.py::test_sensitive_admin_logging_must_not_contain_emails_or_names
tests/security/test_a09_logging_alerting.py::test_sensitive_order_logging_must_not_contain_shipping_address
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a09_logging_alerting.py | Detection suite asserting secure audit logging; fails on vulnerable red-phase code. |

## Remediation

_Pending — populated in the Green phase of this iteration._
