"""Database migrate + seed helpers used by the API lifespan and Docker entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)

logger = logging.getLogger(__name__)


def locate_project_root() -> Path:
    """Locate the directory that contains ``alembic.ini`` and ``database/``."""
    candidates = [
        Path.cwd(),
        Path("/app"),
        Path(__file__).resolve().parents[4],
        *Path.cwd().resolve().parents,
    ]
    for candidate in candidates:
        if (candidate / "alembic.ini").is_file() and (candidate / "database").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not locate alembic.ini next to the database/ directory. "
        "Set the working directory to the project root or copy those files into /app."
    )


def run_alembic_upgrade(database_url: str) -> None:
    """Apply Alembic migrations to head."""
    root = locate_project_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("script_location", str(root / "database" / "migrations"))
    command.upgrade(config, "head")


def run_seed_if_enabled(settings: Settings, session_factory: sessionmaker[Session]) -> None:
    """Run the deterministic seeder when ``seed_on_startup`` is enabled."""
    if not settings.seed_on_startup:
        return
    from database.seeding.seed import seed_database

    with session_factory() as session:
        seed_database(session)
        session.commit()


def prepare_database(settings: Settings) -> tuple[Engine, sessionmaker[Session]]:
    """Create the engine, migrate to head, optionally seed, and return session factory."""
    engine = create_database_engine(settings.database_url)
    logger.info("Running Alembic migrations against the configured database.")
    run_alembic_upgrade(settings.database_url)
    session_factory = create_session_factory(engine)
    run_seed_if_enabled(settings, session_factory)
    return engine, session_factory
