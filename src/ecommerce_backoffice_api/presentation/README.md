# Presentation layer

The outermost layer of the API. FastAPI routers, request/response DTOs,
dependency-injection wiring, exception handlers and the OpenAPI customisation
that produces the `/docs`, `/redoc` and `/openapi.json` contract.

## Dependency rule

**Depends on: all inner layers, wires them together.**

- Composes concrete `infrastructure` adapters and injects them into
  `application` use cases (the composition root lives here).
- Translates domain/application exceptions into HTTP responses
  (RFC 9457 Problem Details, introduced properly in iter-01).
- Must NOT contain business rules - it only adapts HTTP to use cases.

Nothing imports `presentation`. It is the top of the dependency graph.
