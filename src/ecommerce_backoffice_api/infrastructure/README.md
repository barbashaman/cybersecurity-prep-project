# Infrastructure layer

Concrete adapters: SQLAlchemy repositories, Alembic wiring, HTTP clients to
third-party services, configuration loading, password hashing, token issuers.
Each adapter implements a `Protocol` port declared in `application`.

## Dependency rule

**Depends on: `domain` and `application`.**

- Implements ports from `application`; imports entities from `domain`.
- Must NOT import `presentation`.
- This is the only layer allowed to touch external systems (DB, network, disk,
  crypto libraries, environment).

Swapping Postgres for an in-memory fake, or MD5 for Argon2 (iter-07), is a
change confined to this layer - callers depend on the port, not the adapter.
