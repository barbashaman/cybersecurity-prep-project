Document Name: ADR 0004 - Countdown against OWASP Top 10:2025 (Web)
Covered Elements: Risk taxonomy choice, A10->A01 ordering, API Top 10 cross-referencing
Creation Date: 26/07/2026-13:33:00.000

# ADR 0004: Countdown against the OWASP Top 10:2025 (Web)

- **Status:** Accepted
- **Context:** The portfolio must map features to a recognised risk taxonomy.
  The role is API and cloud-native SaaS focused.
- **Decision:** Structure ten iterations against the **OWASP Top 10:2025 (Web)**
  list, counted down **A10 → A01** so the finale is A01 Broken Access Control
  (the risk identified as roughly 40% of documented API attacks). Each advisory
  additionally **cross-references the OWASP API Security Top 10**, since the
  target audience is API-centric.
- **Alternatives:** Use the API Top 10 as the primary spine — rejected as the
  primary spine because the Web list is the broader, more widely recognised
  reference; the API mapping is layered on per advisory instead.
- **Consequences:** The iteration mapping in `iteration-playbook.md` is fixed;
  each iteration ships a genuine feature that carries its risk rather than a
  contrived flaw.
