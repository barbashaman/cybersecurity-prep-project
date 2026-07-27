"""Application configuration loaded from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_version() -> str:
    env_version = os.environ.get("VERSION")
    if env_version:
        return env_version.strip()
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def _read_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed application settings."""

    environment: str
    version: str
    debug: bool
    expose_docs: bool
    cors_allow_origins: tuple[str, ...]
    api_host: str
    api_port: int
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    seed_on_startup: bool
    theme_hmac_secret: str
    pii_encryption_key: str

    @classmethod
    def from_env(cls) -> Settings:
        environment = os.environ.get("APP_ENV", "development").strip().lower() or "development"
        origins_raw = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
        origins = tuple(origin.strip() for origin in origins_raw.split(",") if origin.strip())
        # nosec B105 - intentional demo default; hardened in a later iteration.
        jwt_secret = os.environ.get(
            "JWT_SECRET",
            "phase1b-demo-only-jwt-secret-change-me",
        )
        theme_hmac_secret = os.environ.get(
            "THEME_HMAC_SECRET",
            "phase1b-demo-only-theme-hmac-secret-change-me",
        )
        pii_encryption_key = os.environ.get("PII_ENCRYPTION_KEY", "")
        return cls(
            environment=environment,
            version=_read_version(),
            debug=_read_bool("DEBUG", default=False),
            expose_docs=_read_bool("EXPOSE_DOCS", default=environment != "production"),
            cors_allow_origins=origins or ("http://localhost:3000",),
            api_host=os.environ.get("API_HOST", "0.0.0.0"),  # noqa: S104
            api_port=int(os.environ.get("API_PORT", "8000")),
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql+psycopg://backoffice:change_me_local_only@localhost:5432/backoffice",
            ),
            jwt_secret=jwt_secret,
            jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
            jwt_expire_minutes=int(os.environ.get("JWT_EXPIRE_MINUTES", str(60 * 24 * 7))),
            seed_on_startup=_read_bool("SEED_ON_STARTUP", default=True),
            theme_hmac_secret=theme_hmac_secret,
            pii_encryption_key=pii_encryption_key,
        )
