"""Detection tests for OWASP A02 — Security Misconfiguration (iter-09)."""

from __future__ import annotations

import os

from ecommerce_backoffice_api.infrastructure.config import Settings


def test_settings_must_default_to_secure_values() -> None:
    # Threat category: OWASP A02 (Security Misconfiguration).
    # Attack path: default boot with weak-by-default flags (debug mode, wildcard CORS).
    # Expected secure behavior: secure defaults on first run without operator tuning.
    # Failure impact: verbose internals + broad browser origins can increase exploitability.
    # Arrange

    # Act
    settings = Settings.from_env()

    # Assert
    assert settings.debug is False
    assert "*" not in settings.cors_allow_origins


def test_production_must_hide_docs_by_default() -> None:
    # Threat category: OWASP A02 (Security Misconfiguration).
    # Attack path: production deployment forgets to explicitly disable docs exposure.
    # Expected secure behavior: API docs remain hidden in production by default.
    # Failure impact: attackers gain endpoint discovery and schema intelligence.
    # Arrange
    previous = os.environ.get("APP_ENV")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("EXPOSE_DOCS", None)

        # Act
        settings = Settings.from_env()
    finally:
        if previous is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous

    # Assert
    assert settings.expose_docs is False
