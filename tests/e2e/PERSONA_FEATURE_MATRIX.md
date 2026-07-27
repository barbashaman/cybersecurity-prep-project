# E2E Persona-Feature Matrix

Robot Framework journeys under `tests/e2e`. Suites skip when the seeded API/web
stack is unreachable (`TOOLKIT_BASE_URL`, `WEB_BASE_URL`).

| Persona | Auth | Stores / catalog | Checkout | Shipping | Orders | Admin / governance | Misconfig headers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| admin | allow | cross-store allow | n/a | n/a | allow | create store + revenue + user directory | via shared web headers |
| store_owner_primary | allow | own catalog create + web browse | deny (negative) | n/a | manage when tenant matches | deny admin (covered functional) | via shared web headers |
| store_owner_secondary | allow | foreign catalog deny (A01) | n/a | n/a | n/a | n/a | via shared web headers |
| customer | allow | own catalog + web | purchase lifecycle | allow | own orders web/API | deny admin (A01) | Secure cookie + CSP/HSTS |
| delivery_manager | allow | n/a | deny | deny | anonymized API + web | n/a | via shared web headers |
| anonymous | me → 401 | n/a | n/a | n/a | n/a | admin → 401 | public `/health` only |

## Traceability

- `customer_purchase.robot` — purchase lifecycle
- `store_owner_catalog.robot` — catalog/order management
- `admin_governance.robot` — cross-store governance
- `delivery_privacy.robot` — privacy-safe order visibility
- `access_control_negative.robot` — broken access control negatives
- `security_misconfiguration.robot` — CSP/HSTS/Secure cookie + auth boundary
