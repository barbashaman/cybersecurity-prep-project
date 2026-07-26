"""Detection tests for OWASP A09 — Security Logging and Alerting Failures (iter-02).

These tests assert *secure* behaviour:
- authorization failures must produce an audit-trail event
- sensitive admin paths must not emit bearer tokens or PII (emails, names,
  shipping addresses) into application log records

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import logging

import pytest

from ecommerce_backoffice_api.application.use_cases.admin import ListUsers
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.application.use_cases.orders import GetOrder
from ecommerce_backoffice_api.application.use_cases.products import UpdateProduct
from ecommerce_backoffice_api.domain.entities import AuditEvent, Order, Product, User
from ecommerce_backoffice_api.domain.enums import AuditOutcome, OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError

pytestmark = pytest.mark.security

_AUDIT_LOGGER_NAME = "ecommerce_backoffice_api.audit"


class _FakeAuditEventRepository:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._next_id = 1

    def add(self, event: AuditEvent) -> AuditEvent:
        event.id = self._next_id
        self._next_id += 1
        self.events.append(event)
        return event

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        return list(reversed(self.events[-limit:]))


class _FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    def get_by_id(self, user_id: int) -> User | None:
        for user in self._users:
            if user.id == user_id:
                return user
        return None

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        for user in self._users:
            if user.email == normalized:
                return user
        return None

    def list_all(self) -> list[User]:
        return list(self._users)

    def add(self, user: User) -> User:
        self._users.append(user)
        return user

    def update_password(self, user_id: int, password_hash: str) -> User:
        for user in self._users:
            if user.id == user_id:
                user.password_hash = password_hash
                return user
        raise LookupError(user_id)


class _FakeProductRepository:
    def __init__(self, product: Product) -> None:
        self._product = product

    def list_for_store(self, store_id: int) -> list[Product]:
        return [self._product] if self._product.store_id == store_id else []

    def get_by_id(self, product_id: int) -> Product | None:
        if self._product.id == product_id:
            return self._product
        return None

    def add(self, product: Product) -> Product:
        return product

    def save(self, product: Product) -> Product:
        self._product = product
        return product


class _FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self._order = order

    def list_for_store(self, store_id: int) -> list[Order]:
        return [self._order] if self._order.store_id == store_id else []

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        if self._order.store_id == store_id and self._order.customer_user_id == customer_user_id:
            return [self._order]
        return []

    def get_by_id(self, order_id: int) -> Order | None:
        if self._order.id == order_id:
            return self._order
        return None

    def add(self, order: Order) -> Order:
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        self._order.status = status
        return self._order


def _admin() -> User:
    return User(
        id=1,
        email="admin@example.test",
        password_hash="unused",
        role=UserRole.ADMIN,
        full_name="Ada Admin",
        store_id=None,
    )


def _store_owner() -> User:
    return User(
        id=2,
        email="owner1@example.test",
        password_hash="unused",
        role=UserRole.STORE_OWNER,
        full_name="Ollie Owner",
        store_id=1,
    )


def _customer() -> User:
    return User(
        id=10,
        email="customer1@example.test",
        password_hash="unused",
        role=UserRole.CUSTOMER,
        full_name="Casey Customer",
        store_id=1,
    )


def _product() -> Product:
    return Product(
        id=7,
        store_id=1,
        name="Trail Bottle",
        description="Insulated",
        price_cents=1999,
        is_active=True,
    )


def _order() -> Order:
    return Order(
        id=42,
        store_id=1,
        customer_user_id=10,
        status=OrderStatus.PACKED,
        customer_email="customer1@example.test",
        customer_full_name="Casey Customer",
        shipping_address="1 Demo Way, Lisbon",
    )


def _combined_log_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_authorization_failure_must_produce_audit_event() -> None:
    """Secure: denied product updates must leave an authorization_denied audit row."""
    audit_repo = _FakeAuditEventRepository()
    audit_trail = AdminAuditTrail(audit_repo)
    use_case = UpdateProduct(_FakeProductRepository(_product()), audit_trail)
    outsider = _customer()

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=outsider, product_id=7, name="Hijacked")

    denied = [
        event
        for event in audit_repo.events
        if event.outcome is AuditOutcome.AUTHORIZATION_DENIED and event.action == "product.update"
    ]
    assert denied, "authorization failures must be persisted on the audit trail"
    assert denied[0].actor_user_id == outsider.id
    assert denied[0].resource_id == "7"


def test_list_users_authorization_failure_must_produce_audit_event() -> None:
    """Secure: denied admin directory access must be audited."""
    audit_repo = _FakeAuditEventRepository()
    audit_trail = AdminAuditTrail(audit_repo)
    use_case = ListUsers(_FakeUserRepository([_admin(), _store_owner()]), audit_trail)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=_store_owner())

    denied = [
        event
        for event in audit_repo.events
        if event.outcome is AuditOutcome.AUTHORIZATION_DENIED and event.action == "user.list"
    ]
    assert denied, "authorization failures for user.list must be persisted"


def test_sensitive_admin_logging_must_not_contain_bearer_tokens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Secure: admin success logs must not echo bearer access tokens."""
    audit_repo = _FakeAuditEventRepository()
    audit_trail = AdminAuditTrail(audit_repo)
    use_case = ListUsers(_FakeUserRepository([_admin(), _customer()]), audit_trail)
    access_token = "eyJhbGciOiJIUzI1NiJ9.vulnerable-token-fixture.signature"

    with caplog.at_level(logging.INFO, logger=_AUDIT_LOGGER_NAME):
        use_case.execute(actor=_admin(), access_token=access_token)

    combined = _combined_log_text(caplog)
    assert access_token not in combined
    assert "Bearer " not in combined


def test_sensitive_admin_logging_must_not_contain_emails_or_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Secure: admin success logs must not contain actor/subject emails or names."""
    audit_repo = _FakeAuditEventRepository()
    audit_trail = AdminAuditTrail(audit_repo)
    admin = _admin()
    customer = _customer()
    use_case = ListUsers(_FakeUserRepository([admin, customer]), audit_trail)

    with caplog.at_level(logging.INFO, logger=_AUDIT_LOGGER_NAME):
        use_case.execute(actor=admin, access_token="unused-token")

    combined = _combined_log_text(caplog)
    assert admin.email not in combined
    assert customer.email not in combined
    assert admin.full_name not in combined
    assert customer.full_name not in combined


def test_sensitive_order_logging_must_not_contain_shipping_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Secure: admin order reads must not log customer shipping addresses."""
    audit_repo = _FakeAuditEventRepository()
    audit_trail = AdminAuditTrail(audit_repo)
    order = _order()
    use_case = GetOrder(_FakeOrderRepository(order), audit_trail)

    with caplog.at_level(logging.INFO, logger=_AUDIT_LOGGER_NAME):
        use_case.execute(
            actor=_admin(),
            order_id=42,
            access_token="eyJhbGciOiJIUzI1NiJ9.order-read-token.signature",
        )

    combined = _combined_log_text(caplog)
    assert order.shipping_address not in combined
    assert order.customer_email not in combined
