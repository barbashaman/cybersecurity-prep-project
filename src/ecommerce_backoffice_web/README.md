# Web service (`ecommerce_backoffice_web`)

A separate Jinja2 server-rendered front end, deliberately decoupled from the
API service and sized for wrapping in an Android WebView. It talks to the API
over HTTP using the same OpenAPI contract external clients use - it holds no
direct database access.

## Dependency rule

- Depends on the API only through its HTTP contract (`API_BASE_URL`).
- Must NOT import `ecommerce_backoffice_api` packages directly. Keeping the two
  services at arm's length is what makes the DAST surface realistic and lets
  the web tier be scaled or replaced independently.

Phase 1 ships the package skeleton only; templates and routes arrive in
Phase 1b.
