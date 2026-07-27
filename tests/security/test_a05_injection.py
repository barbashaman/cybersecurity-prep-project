"""Detection tests for OWASP A05 — Injection (iter-06).

These tests assert *secure* behaviour:
- product search must treat the query as a bound literal (no SQL side effects /
  tautology bypass via concatenation)
- order notes must be HTML-escaped in rendered web output (no raw ``<script>``)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). Wired into the PR-required quality-gate core
pyramid (offline security marker suite).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ecommerce_backoffice_api.infrastructure.persistence.models import (
    Base,
    ProductModel,
    StoreModel,
)
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyProductRepository,
)
from tests.toolkit.payloads.builders import (
    sql_injection_like_bypass_query,
    stored_xss_order_notes,
)

pytestmark = pytest.mark.security

_WEB_TEMPLATES = (
    Path(__file__).resolve().parents[2] / "src" / "ecommerce_backoffice_web" / "templates"
)


def _session_with_catalog() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    store_a = StoreModel(public_id=str(uuid.uuid4()), name="Northwind")
    store_b = StoreModel(public_id=str(uuid.uuid4()), name="Contoso")
    session.add_all([store_a, store_b])
    session.flush()
    session.add_all(
        [
            ProductModel(
                store_id=store_a.id,
                name="Trail Jacket",
                description="outdoor",
                price_cents=9900,
                is_active=True,
                stock_quantity=5,
            ),
            ProductModel(
                store_id=store_a.id,
                name="Camp Mug",
                description="kitchen",
                price_cents=1200,
                is_active=True,
                stock_quantity=20,
            ),
            ProductModel(
                store_id=store_b.id,
                name="Gadget Pro",
                description="electronics",
                price_cents=49900,
                is_active=True,
                stock_quantity=3,
            ),
        ]
    )
    session.commit()
    return session


def test_product_search_must_use_parameterized_queries() -> None:
    """Secure: injection payloads must not bypass LIKE matching via SQL concat."""
    session = _session_with_catalog()
    try:
        repo = SqlAlchemyProductRepository(session)
        store_id = session.scalars(select(StoreModel.id).order_by(StoreModel.id)).first()
        assert store_id is not None

        before_count = len(session.scalars(select(ProductModel)).all())
        results = repo.search_for_store(store_id, sql_injection_like_bypass_query())

        # Bound-parameter search treats the payload as a literal name fragment.
        assert results == []
        assert len(session.scalars(select(ProductModel)).all()) == before_count
        assert all(product.store_id == store_id for product in results)
    finally:
        session.close()


def test_order_notes_must_be_html_escaped_in_rendered_output() -> None:
    """Secure: rendered notes must not contain a raw script element."""
    env = Environment(
        loader=FileSystemLoader(str(_WEB_TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("partials/order_notes.html")
    payload = stored_xss_order_notes()
    rendered = template.render(notes=payload)

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
