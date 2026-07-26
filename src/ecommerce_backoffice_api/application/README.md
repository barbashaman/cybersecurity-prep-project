# Application layer

Use cases (interactors) and the ports they depend on. Ports are declared as
`typing.Protocol` so that infrastructure adapters are structurally - not
nominally - bound. This is the Dependency Inversion seam that lets the same
use case run against a real repository or a fake.

## Dependency rule

**Depends on: `domain` only.**

- May import from `domain`.
- May define `Protocol` ports that `infrastructure` implements.
- Must NOT import `infrastructure` or `presentation`.
- Must NOT import web frameworks. Use cases receive already-validated data.

Interface Segregation is load-bearing: a `DeliveryManager` port exposes only
anonymised, non-PII methods, so a whole class of access-control mistakes is
impossible to express (relevant to iter-04, iter-05, iter-10).
