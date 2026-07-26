Document Name: Architecture Overview
Covered Elements: System topology, Clean Architecture layers and dependency rule, black-box/white-box testing seam, security iteration lifecycle
Creation Date: 26/07/2026-13:20:00.000

# Architecture Overview

## System topology

Three long-running services plus two on-demand tooling services, all defined as
Infrastructure-as-Code in `docker-compose.yml` on an isolated bridge network:

```
        +------------------+        +----------------------+
 host   |  api  :8000      |<-------|  web  :8080 (Jinja2) |
 ports  |  FastAPI/OpenAPI |  HTTP  |  Android-WebView UI  |
        +---------+--------+        +----------------------+
                  |
                  v
        +------------------+     on demand:
        | database :5432   |     zap :8090 (DAST)  tests (toolkit runner)
        | PostgreSQL       |
        +------------------+
```

- **api** — FastAPI. Auto-generates the OpenAPI 3.1 contract at `/docs`,
  `/redoc`, `/openapi.json`. The exported `openapi.json` is a first-class build
  artifact: input to the ZAP API scan and to contract tests, published as CI
  evidence, and surfaced in the Swagger banner on every full-app start.
- **web** — a separate Jinja2 server-rendered service. Talks to the API only
  over its HTTP contract; holds no database access.
- **database** — PostgreSQL. Ephemeral (tmpfs) and freshly seeded for every
  pipeline run; a persistent volume is used locally via the compose override.
- **zap** — OWASP ZAP, started on demand for DAST.
- **tests** — the toolkit runner image carrying pytest/pytest-bdd, Playwright
  and Robot Framework.

## Clean Architecture and the dependency rule

The API is four layers with a strictly inward dependency rule; each layer's
`README.md` states its rule at the point of violation:

```
presentation  ->  application  ->  domain
      \_____________ infrastructure ______/   (implements application ports)
```

- **domain** — entities, value objects, authorization policies. Zero framework
  imports. Security-relevant constants are typed enums, never magic strings.
- **application** — use cases and ports declared as `typing.Protocol`.
- **infrastructure** — SQLAlchemy repositories, HTTP adapters, config, crypto.
  The only layer that touches external systems.
- **presentation** — routers, DI wiring (composition root), error handlers.

SOLID is load-bearing, not decorative:

- **Dependency Inversion** is the seam that lets one test suite run black-box
  against the container and white-box against in-process objects.
- **Interface Segregation** keeps a delivery manager's port from exposing
  PII-carrying methods *at all*, making a class of access-control mistakes
  impossible to express (relevant to iter-04, iter-05, iter-10).

## The black-box / white-box testing seam

`tests/toolkit` is a dependency-injected framework. `ExecutionContext` is
constructor-injected with a resolved `Environment`, an `IdentityProvider` and a
`TransportClient`. The `ToolkitContainer` composition root selects the transport
from `TOOLKIT_TRANSPORT`:

- `http` → `HttpTransportClient` → same scenario runs **black-box** over HTTP.
- `in_process` → `InProcessTransportClient` → same scenario runs **white-box**
  against use cases.

Gherkin under `tests/behaviour/features/` is the single source of truth; the
`api`, `e2e` and `security` suites bind those scenarios to runners.

## Security iteration lifecycle

Ten iterations, each on `iter-<NN>-owasp-<risk>-<slug>` branched from `main`:

1. **Red** — ship a genuine feature that carries the risk by design.
2. **Red** — a detection test plus an auto-generated advisory prove the flaw.
3. **Green** — remediate.
4. **Validate** — full suite green.
5. **Tag & merge** — two tags per iteration (`*-vulnerable`, `*-remediated`).

A reviewer can check out the `*-vulnerable` tag and watch the pipeline fail on
demand. That reproducible red-to-green transition is the portfolio's core
artifact. See [`../iteration-playbook.md`](../iteration-playbook.md).

## Phase boundaries

- **Phase 1 (this bootstrap)** — scaffolding, IaC, CI/CD, scripts, toolkit
  skeleton, and a minimal *operational* API (health/version/OpenAPI only). No
  e-commerce domain code.
- **Phase 1b** — baseline application: domain model, auth, RBAC, CRUD, Jinja2
  UI, database seeder.
- **Phase 2** — the A10→A01 countdown.
- **Phase 3** — golden master: all risks remediated, consolidated posture report.
