# Database

Alembic migrations and the deterministic seeder for the pre-seeded baseline
state every pipeline and test run launches against.

```
migrations/   # Alembic revisions (Phase 1b baseline schema)
seeding/      # deterministic seed: 1 admin, 2 store owners, 2 customers,
              #   1 delivery manager, 2 stores, 12 products each, staged orders
```

The compose `database` service is **ephemeral (tmpfs)** in CI so every run
starts from a clean, freshly seeded state; the local compose override swaps in a
persistent volume.

## Seed credentials (demo-only)

Password for all seeded users: `ChangeMeDemoOnly!`

| Email | Role |
| --- | --- |
| `admin@example.com` | admin |
| `owner1@example.com` | store_owner (Northwind Outfitters) |
| `owner2@example.com` | store_owner (Contoso Gadgets) |
| `customer1@example.com` | customer (store 1) |
| `customer2@example.com` | customer (store 2) |
| `delivery@example.com` | delivery_manager |

The seeder is idempotent: if `admin@example.com` already exists, seeding is
skipped. The API entrypoint and FastAPI lifespan both call migrate + seed on
startup.
