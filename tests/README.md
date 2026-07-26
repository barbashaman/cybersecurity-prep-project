# Tests

A single test toolkit drives four suites. Gherkin under `behaviour/features/`
is the single source of truth; the suites bind those scenarios to different
transports and runners.

```
toolkit/      Reusable, dependency-injected framework (no test logic).
  context/    ExecutionContext + DI container.
  clients/    Transport client protocols (HTTP / in-process).
  identities/ Multi-role token matrix (admin, owner, customer, delivery).
  assertions/ Domain-aware assertion helpers.
  payloads/   Request/payload builders and fixtures.
  reporting/  Unified HTML dashboard renderer + AdvisoryGenerator.
behaviour/features/  Gherkin - the single source of truth.
api/          pytest-bdd + Playwright APIRequestContext (integration/API).
e2e/          Robot Framework (end-to-end, web functional).
security/     ZAP-proxied and role-matrix security suites.
```

## Black-box vs white-box

`ExecutionContext` is constructor-injected with a resolved environment, an
identity provider and a transport client. Selecting the `http` transport runs
a scenario black-box against the running container; selecting the `in_process`
transport runs the very same scenario white-box against in-process use cases.
Dependency Inversion is what makes one scenario serve both.

Phase 1 ships interfaces and the DI container only - no test logic yet.
