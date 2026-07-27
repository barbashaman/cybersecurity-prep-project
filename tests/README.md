# Tests

A modular toolkit plus a layered pyramid. Gherkin under `behaviour/features/`
remains the scenario source of truth for API/E2E bindings; newer layers add
persona-feature coverage with pytest (and Robot for E2E).

```
toolkit/      Reusable, dependency-injected framework (no test logic).
behaviour/    Gherkin features (API/E2E bindings).
domain/       Pure domain policy smoke (PR-required).
component/    Isolated use-case tests with fakes (PR-required).
database/     SQLite repository/model constraints (PR-required).
integration/  Use-case + SQLAlchemy persistence (PR-required).
security/     OWASP AAA detection suites, in-process (PR-required).
performance/  SLO benches: performance_fast (PR) / performance_extended (nightly).
functional/   HTTP persona-feature contracts against a seeded stack (nightly).
api/          pytest-bdd / API smoke against a seeded stack (nightly).
e2e/          Robot Framework persona journeys (nightly).
```

## CI tiers

| Tier | Workflow | Trigger | Suites |
| --- | --- | --- | --- |
| **A — required** | `ci-quality-gate` | every push + every PR to `main` | lint, typecheck, import contracts, core pyramid (`not performance_extended`), Docker image builds |
| **B — extended** | `ci-extended` | nightly schedule, `workflow_dispatch`, and PRs to `main` that touch stack-backed test paths | functional + API smoke, `performance_extended`, Robot E2E |
| **C — scanners** | `ci-sast`, `ci-dast`, `ci-supply-chain` | every push + every PR to `main` | Bandit/Semgrep, ZAP, pip-audit/Trivy |

Branch protection on `main` requires the `quality-gate` job. Extended suites are
promoted into Tier A only after they stay green on the nightly path.

Local mirrors:

```bash
bash scripts/run_tests_core.sh          # Tier A pytest subset
bash scripts/run_all_tests.sh           # stack-backed API + E2E + security
TOOLKIT_BASE_URL=http://localhost:8000 WEB_BASE_URL=http://localhost:8080 \
  PYTHONPATH="src:." robot tests/e2e    # E2E only
```

## Black-box vs white-box

`ExecutionContext` is constructor-injected with a resolved environment, an
identity provider and a transport client. Selecting the `http` transport runs
a scenario black-box against the running container; selecting the `in_process`
transport runs the very same scenario white-box against in-process use cases.
Dependency Inversion is what makes one scenario serve both.
