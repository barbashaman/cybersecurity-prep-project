# Performance Persona-Feature Matrix

SLO coverage for critical paths. Fast tests are PR-safe; extended tests are
opt-in via ``performance_extended``.

| Persona | Auth login | Checkout | Shipping quote | Order list / projection |
| --- | --- | --- | --- | --- |
| admin | structural + Argon2 SLO | n/a (not primary actor) | allowed (shared path) | full PII projection under SLO |
| store_owner | Argon2 burst (extended) | n/a | allowed (shared path) | covered via admin-equivalent list shape |
| customer | Argon2 + structural SLO | place-order under SLO | quote under SLO | filtered own-orders under SLO |
| delivery_manager | n/a | denied (authz path not timed) | denial under authz SLO | anonymized projection under SLO + ratio vs admin |

## Traceability

- `test_critical_path_slos.py` — auth, checkout, shipping, admin list (`performance_fast`)
- `test_persona_projection_slos.py` — admin vs delivery projection, customer filter, shipping deny (`performance_fast`)
- `test_extended_load.py` — larger lists, bursts (`performance_extended`)
