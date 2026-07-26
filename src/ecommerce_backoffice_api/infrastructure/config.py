"""Application configuration loaded from the environment.

Phase 1 ships an honest, deliberately un-hardened baseline: ``DEBUG`` defaults
on, CORS is wide open and ``/docs`` is exposed. iter-09 (A02 Security
Misconfiguration) is where these become env-driven and locked down. Keeping the
config in one typed place is what makes that later change a single, reviewable
diff.
"""

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

    version: str
    debug: bool
    expose_docs: bool
    cors_allow_origins: tuple[str, ...]
    api_host: str
    api_port: int

    @classmethod
    def from_env(cls) -> Settings:
        origins_raw = os.environ.get("CORS_ALLOW_ORIGINS", "*")
        origins = tuple(o.strip() for o in origins_raw.split(",") if o.strip())
        return cls(
            version=_read_version(),
            debug=_read_bool("DEBUG", default=True),
            expose_docs=_read_bool("EXPOSE_DOCS", default=True),
            cors_allow_origins=origins or ("*",),
            api_host=os.environ.get("API_HOST", "0.0.0.0"),  # nosec B104  # noqa: S104
            api_port=int(os.environ.get("API_PORT", "8000")),
        )
