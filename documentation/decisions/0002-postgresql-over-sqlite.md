Document Name: ADR 0002 - PostgreSQL over SQLite
Covered Elements: Database engine choice, ephemeral seeded database per run
Creation Date: 26/07/2026-13:31:00.000

# ADR 0002: PostgreSQL over SQLite

- **Status:** Accepted
- **Context:** The target role is cloud-native SaaS. Several iterations depend
  on production-grade database semantics: real constraints and transactional
  isolation for the stock race condition (iter-05), and injection behaviour that
  matches a server engine (iter-06).
- **Decision:** Use **PostgreSQL** via SQLAlchemy + Alembic, containerised. Each
  pipeline run gets an ephemeral, freshly seeded database (tmpfs), so runs are
  independent and reproducible.
- **Alternatives:** SQLite is simpler and file-portable but diverges on
  concurrency, constraint enforcement and SQL dialect — precisely the behaviours
  the security iterations must exercise faithfully.
- **Consequences:** A running database is required for the API and for DAST; the
  compose stack and healthchecks account for this. Local development uses a
  persistent volume via the compose override.
