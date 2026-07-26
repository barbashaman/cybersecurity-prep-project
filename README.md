# E-Commerce Backoffice SaaS — OWASP Top 10:2025 Countdown Portfolio

A Dockerized **FastAPI + Jinja2 + PostgreSQL** e-commerce backoffice SaaS, built
as a security-testing portfolio for a **Senior Test Engineer — Cybersecurity**
role. The application is evolved across **10 iterations**, each deliberately
introducing one of the **OWASP Top 10:2025** risks (counted down from **A10 to
A01**), proving it with automated detection, generating an advisory, then
remediating it — a reproducible red-to-green transition captured in the CI
evidence trail.

> **Phase 1 (this bootstrap)** ships scaffolding, infrastructure, CI/CD and
> scripts **only** — no application code. Application code arrives in Phase 1b.

---

## Architecture at a glance

- **API** — FastAPI, auto-generating an OpenAPI 3.1 contract at `/docs`,
  `/redoc`, `/openapi.json`. Structured in four Clean Architecture layers
  (`domain` → `application` → `infrastructure` → `presentation`) with a strictly
  inward dependency rule.
- **Web** — a separate Jinja2 server-rendered service, Android-WebView friendly,
  talking to the API purely over its HTTP contract.
- **Database** — PostgreSQL via SQLAlchemy + Alembic. Every pipeline run gets an
  ephemeral, freshly seeded database.
- **Infrastructure** — everything runs under `docker-compose` (IaC).
- **Test toolkit** — a modular, dependency-injected framework (`tests/toolkit/`)
  that runs the same Gherkin scenarios black-box (HTTP against the container) or
  white-box (in-process against use cases).

See [`documentation/architecture/overview.md`](documentation/architecture/overview.md)
and the ADRs under [`documentation/decisions/`](documentation/decisions/).

---

## Prerequisites

Run the gate first — every script sources it and fails with a named error if a
prerequisite is missing:

```bash
bash scripts/verify_prerequisites.sh
```

| Requirement | Why | Install |
| --- | --- | --- |
| **Docker + docker compose** (WSL2 backend on Windows) | runs the whole stack | `wsl --install` (reboot), then Docker Desktop |
| **Python 3.12** | Playwright/Robot wheels; pinned in containers and locally | `py install 3.12` / `winget install Python.Python.3.12` |
| **gh CLI (authenticated)** | create/push the private repo, trigger pipelines | `gh auth login` |

## Quick start

```bash
# 1. Verify the environment
bash scripts/verify_prerequisites.sh

# 2. Build and start the full stack (prints the live Swagger banner on success)
bash scripts/run_app.sh

# 3. Run the suites (each gates on the running app version first)
bash scripts/run_tests_api.sh
bash scripts/run_tests_e2e.sh
bash scripts/run_tests_security.sh
bash scripts/run_all_tests.sh
```

---

## Repository layout

```
src/ecommerce_backoffice_api/   # domain / application / infrastructure / presentation
src/ecommerce_backoffice_web/   # Jinja2 web tier
database/                       # Alembic migrations + seeding
tests/                          # DI toolkit + api / e2e / security / behaviour suites
scripts/                        # run_app.sh, run_tests_*.sh, lib/common.sh
docker/                         # api / web / tests Dockerfiles
documentation/                  # architecture, ADRs, advisories, api-contract
.github/                        # workflows + publish-reports composite action
reports/                        # local mirror of the Tier-2 archive layout (gitignored)
```

## DevSecOps pipeline

| Workflow | Purpose |
| --- | --- |
| `ci-quality-gate` | ruff, mypy `--strict`, unit tests, image build |
| `ci-sast` | Bandit + Semgrep, SARIF upload to code scanning |
| `ci-supply-chain` | pip-audit, CycloneDX SBOM, Trivy image scan |
| `ci-dast` | compose + seed + export `openapi.json` + ZAP baseline & API scan |
| `ci-advisory` | generate & commit advisories on iteration branches |

Every job publishes evidence to **two tiers**: per-run Actions artifacts (debug
the run in front of you) and the permanent, browsable **`reports` archive
branch** (the red-to-green evidence trail). See
[`documentation/architecture/reporting.md`](documentation/architecture/reporting.md).

## The countdown

See [`documentation/iteration-playbook.md`](documentation/iteration-playbook.md)
for the per-iteration Red → Red → Green → validate → tag → merge lifecycle and
the full A10→A01 feature/risk mapping.
