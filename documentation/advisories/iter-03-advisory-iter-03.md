Document Name: Advisory iter-03
Covered Elements: Feature and detection for iter-03 — store theme upload and purchase receipts (A08)
Creation Date: 26/07/2026-19:00:00.000

# Security Advisory — A08 Software or Data Integrity Failures

- **Iteration:** iter-03
- **OWASP Top 10:2025 (Web):** A08 Software or Data Integrity Failures
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration / software and data integrity failures (unsigned artifacts, insecure deserialization)

## Summary

Store theme upload accepts unsigned artifacts without HMAC verification, and purchase receipts are serialized/deserialized with `pickle` on untrusted data.

## Detection

This flaw was proven by the failing detection test:

```
tests/security/test_a08_integrity.py::test_theme_upload_must_reject_unsigned_artifact
tests/security/test_a08_integrity.py::test_theme_upload_must_reject_invalid_signature
tests/security/test_a08_integrity.py::test_receipt_store_must_persist_json_not_pickle
tests/security/test_a08_integrity.py::test_receipt_load_must_reject_pickle_payload
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a08_integrity.py | Detection suite asserting secure theme HMAC verification and JSON-only receipt handling; fails on vulnerable red-phase code. |

## Remediation

- Theme uploads require an HMAC-SHA256 hex signature (`X-Artifact-Signature` /
  `signature_hex`) over the artifact bytes; missing or invalid signatures raise
  `ConflictError` and nothing is persisted.
- Receipts are stored as UTF-8 JSON with an embedded `checksum_sha256` of the
  canonical payload; pickle protocol magic and non-JSON blobs are rejected on load.
