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

_Pending — populated in the Green phase of this iteration._

### Planned fixes (not yet applied)

- Restore **Argon2id** (preferred) or strong bcrypt via the `PasswordHasher` port; re-hash seeded credentials.
- **Encrypt sensitive PII at rest** (AES-GCM / Fernet envelope encryption) with KMS-managed keys; do not store cleartext phones/addresses.
- **Secret management** for `WEB_SESSION_SECRET` / encryption keys (no demo defaults in deployable envs).
- Session cookies: `https_only=True` (Secure) + HttpOnly; emit **HSTS** on the web tier.
