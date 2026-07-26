Document Name: Advisory iter-04
Covered Elements: Feature and detection for iter-04 — password reset and session management (A07)
Creation Date: 26/07/2026-20:00:00.000

# Security Advisory — A07 Authentication Failures

- **Iteration:** iter-04
- **OWASP Top 10:2025 (Web):** A07 Authentication Failures
- **OWASP API Security Top 10 cross-reference:** API2:2023 Broken Authentication (credential stuffing, weak tokens, session fixation / missing invalidation)

## Summary

Password-reset tokens are predictable and reusable, login/reset flows lack rate limiting, logout does not revoke bearer tokens, and password-reset confirmation issues a non-expiring session JWT.

## Detection

This flaw was proven by the failing detection test:

```
tests/security/test_a07_authentication.py::test_reset_token_must_not_be_predictable
tests/security/test_a07_authentication.py::test_logout_must_invalidate_access_token
tests/security/test_a07_authentication.py::test_password_reset_request_must_rate_limit_after_burst
tests/security/test_a07_authentication.py::test_login_must_rate_limit_after_failed_attempts
tests/security/test_a07_authentication.py::test_reset_confirm_must_issue_short_lived_session_token
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a07_authentication.py | Detection suite asserting secure reset-token entropy, logout revocation, auth rate limiting, and short-lived post-reset JWTs; fails on vulnerable red-phase code. |

## Remediation

- Reset tokens are `secrets.token_urlsafe(32)`, rotated per request, and consumed on confirm.
- Login and password-reset request bursts raise `RateLimitError` after five attempts.
- Logout adds the bearer token to an in-process revocation set; subsequent parses fail.
- Post-reset session JWTs include `exp` with a 15-minute TTL.
