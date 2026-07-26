# Database

Alembic migrations and the deterministic seeder for the pre-seeded baseline
state every pipeline and test run launches against.

```
migrations/   # Alembic revisions (added in Phase 1b)
seeding/      # deterministic seed: 1 admin, 2 store owners, 2 customers,
              #   1 delivery manager, 2 stores, 10+ products each, staged orders
```

The compose `database` service is **ephemeral (tmpfs)** in CI so every run
starts from a clean, freshly seeded state; the local compose override swaps in a
persistent volume. Phase 1 ships the directory contract only — migrations and
the seeder arrive with the domain model in Phase 1b.
