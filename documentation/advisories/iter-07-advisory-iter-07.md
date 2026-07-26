Document Name: Advisory iter-07
Covered Elements: Feature and detection for iter-07 — PII storage and anonymized delivery view (A04)
Creation Date: 26/07/2026-18:45:00.000

# Security Advisory — A04 Cryptographic Failures

- **Iteration:** iter-07
- **OWASP Top 10:2025 (Web):** A04 Cryptographic Failures
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration / cryptographic failures (weak password hashing, plaintext PII at rest, insecure cookie flags)

## Summary

Credentials are hashed with unsalted MD5, shipping contact PII (`customer_phone` and related order fields) is persisted in plaintext without encryption at rest, and the web session cookie is issued without the `Secure` flag (`SessionMiddleware(https_only=False)`). Delivery managers still receive an anonymized order projection, but the underlying storage and transport crypto controls remain weak.

## Detection

```
tests/security/test_a04_cryptographic_failures.py::test_password_hashes_must_use_strong_kdf_not_md5
tests/security/test_a04_cryptographic_failures.py::test_sensitive_pii_at_rest_must_not_be_plaintext
tests/security/test_a04_cryptographic_failures.py::test_session_cookies_must_include_secure_and_httponly
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a04_cryptographic_failures.py | Detection suite asserting strong password KDFs, encrypted PII at rest, and Secure/HttpOnly session cookies. |

## Remediation

Applied in the green phase of this iteration:

- **Argon2id** password hashing via `Argon2PasswordHasher` / `build_password_hasher()`.
- **Fernet encryption at rest** for `customer_phone` (`EncryptedText` TypeDecorator); key from `PII_ENCRYPTION_KEY` (demo-derived fallback for local/CI only).
- Session cookies: `https_only=True` (Secure) + HttpOnly; **HSTS** (`Strict-Transport-Security`) on the web tier.
- Prefer secret management for `WEB_SESSION_SECRET`, `JWT_SECRET`, and `PII_ENCRYPTION_KEY` in deployable environments.
