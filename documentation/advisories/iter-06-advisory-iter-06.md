Document Name: Advisory iter-06
Covered Elements: Feature and detection for iter-06 — product search + order notes (A05)
Creation Date: 26/07/2026-18:45:00.000

# Security Advisory — A05 Injection

- **Iteration:** iter-06
- **OWASP Top 10:2025 (Web):** A05 Injection
- **OWASP API Security Top 10 cross-reference:** API8:2023 Security Misconfiguration / injection class — SQL injection in product search and XSS via unsanitized order notes

## Summary

Product search concatenates the caller-controlled `q` parameter into raw SQL (`WHERE name LIKE '%{q}%'`), and order notes are accepted without validation then rendered with Jinja2 `|safe`, enabling SQL injection and stored XSS.

## Detection

This flaw was proven by the failing detection tests:

```
tests/security/test_a05_injection.py::test_product_search_must_use_parameterized_queries
tests/security/test_a05_injection.py::test_order_notes_must_be_html_escaped_in_rendered_output
```

## Evidence

| Tool | Identifier | Description |
| --- | --- | --- |
| pytest | tests/security/test_a05_injection.py | Detection suite asserting parameterized search and HTML-escaped notes. |

## Remediation

_Pending — populated in the Green phase of this iteration._

PLAN FIX (A05):
- Parameterized queries / ORM `.ilike()` with bound parameters for product search
- Pydantic validation on `q` and `notes` (length / charset)
- Output encoding: drop Jinja2 `|safe` for order notes
- Content-Security-Policy headers on the web tier
