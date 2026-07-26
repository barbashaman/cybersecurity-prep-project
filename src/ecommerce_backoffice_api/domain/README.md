# Domain layer

The innermost layer. Entities, value objects, domain events, authorization
policies and domain exceptions live here.

## Dependency rule

**Depends on: nothing.** This layer imports only the Python standard library.

Forbidden imports (enforced by the import-linter contract in ``pyproject.toml``
and the quality-gate ``lint-imports`` step):

- No `fastapi`, `sqlalchemy`, `pydantic`, `httpx`, or any framework.
- No `application`, `infrastructure`, or `presentation` modules.

If a domain rule needs data from the outside world, it declares the shape it
needs and lets an outer layer satisfy it. Dependencies point inward only.

Security-relevant constants (roles, permissions, order states) are modelled as
typed `enum.Enum` members here - never as magic strings elsewhere.
