Document Name: Advisory iter-09
Covered Elements: Feature and detection for iter-09 — runtime hardening and secure defaults (A02)
Creation Date: 27/07/2026-10:49:00.000

# Security Advisory — A02 Security Misconfiguration

- **Iteration:** iter-09
- **OWASP Top 10:2025 (Web):** A02 Security Misconfiguration
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration

## Summary

Baseline runtime defaults were permissive (`DEBUG`, broad CORS, and docs exposure). Production deployments required hardened defaults and explicit opt-in for diagnostic surfaces.

## Detection

```
tests/security/test_a02_security_misconfiguration.py::test_settings_must_default_to_secure_values
tests/security/test_a02_security_misconfiguration.py::test_production_must_hide_docs_by_default
```

## Remediation

- Hardened config defaults (`DEBUG=false`, restricted CORS defaults).
- Added environment-aware docs exposure policy (`APP_ENV=production` hides docs unless explicitly overridden).
- Added centralized API security response headers middleware and constrained allowed CORS headers/methods.
