Document Name: ADR 0003 - Pin Python 3.12
Covered Elements: Python runtime version pin (containers and local)
Creation Date: 26/07/2026-13:32:00.000

# ADR 0003: Pin Python 3.12

- **Status:** Accepted
- **Context:** The development host had only a very new Python (3.14.x).
  Playwright for Python and Robot Framework do not reliably publish wheels that
  far ahead, which would force fragile source builds in CI and containers.
- **Decision:** Pin **Python 3.12** everywhere — in `pyproject.toml`
  (`requires-python == 3.12.*`), in the `python:3.12-slim` base images, and via
  `scripts/verify_prerequisites.sh`, which fails with a named error if 3.12 is
  absent.
- **Alternatives:** Track the latest Python — rejected due to missing wheels for
  core test tooling. Pin an older LTS-ish version — 3.12 is recent enough for
  modern typing while having full wheel coverage.
- **Consequences:** Reproducible builds; a hash-pinned lockfile resolves cleanly.
  Revisit when Playwright/Robot publish stable wheels for newer interpreters.
