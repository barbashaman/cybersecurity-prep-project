Document Name: Advisory iter-06
Covered Elements: Feature and detection for iter-06 — product search and order notes (A05)
Creation Date: 26/07/2026-18:30:00.000

# Security Advisory — A05 Injection

- **Iteration:** iter-06
- **OWASP Top 10:2025 (Web):** A05 Injection
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration / Injection (SQL injection, XSS via unsafe template rendering)

## Summary

Product search concatenated untrusted query text into SQL `LIKE` clauses, and order notes were rendered with Jinja2 `|safe`, enabling SQL injection and stored XSS.

## Detection

```
tests/security/test_a05_injection.py::test_product_search_must_use_parameterized_queries
tests/security/test_a05_injection.py::test_order_notes_must_be_html_escaped_in_rendered_output
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a05_injection.py | Detection suite asserting bound-parameter search and HTML-escaped notes. |

## Remediation

- Product search uses SQLAlchemy bound `LIKE` parameters (no string-built SQL).
- Order notes templates rely on Jinja2 autoescape (no `|safe`).
- Notes update payloads are length-bounded via Pydantic `Field(max_length=...)`.
- Web tier emits a baseline `Content-Security-Policy` header.
