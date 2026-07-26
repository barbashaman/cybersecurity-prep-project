"""Request payload builders.

Centralises construction of request bodies so that malicious variants used by
the injection and access-control iterations live beside their valid
counterparts.
"""

from __future__ import annotations

import json
from typing import Any


def json_body(**fields: Any) -> str:
    """Serialise ``fields`` to a compact JSON request body."""
    return json.dumps(fields, separators=(",", ":"), sort_keys=True)


def sql_injection_like_bypass_query() -> str:
    """Return a LIKE-clause SQL injection payload for product search (iter-06).

    Against ``WHERE name LIKE '%{q}%'`` this expands to a tautology that returns
    every row. Against a parameterized ``LIKE :pattern`` it is a literal string.
    """
    return "%' OR 1=1 --"


def stored_xss_order_notes() -> str:
    """Return a stored-XSS payload for order notes rendered with Jinja ``|safe``."""
    return "<script>alert('xss')</script>"
