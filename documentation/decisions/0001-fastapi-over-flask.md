Document Name: ADR 0001 - FastAPI over Flask
Covered Elements: API framework choice, OpenAPI contract generation
Creation Date: 26/07/2026-13:30:00.000

# ADR 0001: FastAPI over Flask

- **Status:** Accepted
- **Context:** The project needs a Python RESTful API whose contract is a
  first-class, machine-readable artifact — it feeds the ZAP API scan, contract
  tests, and the published evidence trail.
- **Decision:** Use **FastAPI**. It auto-generates an OpenAPI 3.1 document
  (`/openapi.json`, `/docs`, `/redoc`) with zero extra code, has first-class
  Pydantic validation (which several iterations rely on), and native async.
- **Alternatives:** Flask would require `flask-smorest`/`apispec` plumbing and
  bolt-on validation to reach parity.
- **Consequences:** The exported `openapi.json` becomes the pivot of the DAST
  and contract-testing story. `/docs` exposure becomes an explicit,
  per-environment policy (deliberately open in the Phase 1 baseline; hardened in
  iter-09 / A02).
