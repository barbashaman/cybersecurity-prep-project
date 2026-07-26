"""Request payload builders (skeleton).

Centralises construction of request bodies so that malicious variants used by
the injection and access-control iterations live beside their valid
counterparts. Concrete builders arrive with the features they exercise.
"""

from __future__ import annotations

import json
from typing import Any


def json_body(**fields: Any) -> str:
    """Serialise ``fields`` to a compact JSON request body."""
    return json.dumps(fields, separators=(",", ":"), sort_keys=True)
