Document Name: ADR 0005 - Clean Architecture with enforced inward dependency rule
Covered Elements: Layering, Protocol ports, DI composition root, import discipline
Creation Date: 26/07/2026-13:34:00.000

# ADR 0005: Clean Architecture with an enforced inward dependency rule

- **Status:** Accepted
- **Context:** The same test suite must run black-box against a container and
  white-box against in-process objects, and some ports must be incapable of
  leaking PII by construction.
- **Decision:** Four layers — `domain`, `application`, `infrastructure`,
  `presentation` — with a strictly inward dependency rule. Ports are
  `typing.Protocol`; the composition root lives in `presentation`. Each layer's
  `README.md` documents its rule; a Phase 1b import-linter contract will enforce
  it in CI.
- **Alternatives:** A conventional layered/MVC service — rejected because it
  weakens the Dependency Inversion seam that makes the dual black/white-box
  execution possible.
- **Consequences:** Swapping an adapter (e.g. MD5 → Argon2 in iter-07) is a
  change confined to `infrastructure`. Interface Segregation makes the delivery
  manager's PII-free view a compile-time guarantee (iter-04/05/10).
