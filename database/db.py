"""SENTINEL AI - Database Session Manager.

Provides:
- ``engine`` — the SQLAlchemy engine (created from ``settings.database_url``).
- ``SessionLocal`` — a session factory.
- ``get_db()`` — a FastAPI dependency that yields a database session.
- ``init_db()`` — creates all tables defined via the ORM models.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_settings = get_settings()


def _build_engine() -> Engine:
    """Create a SQLAlchemy :class:`Engine` from the application settings.

    Handles SQLite-specific configuration (e.g. enabling foreign keys)
    as well as PostgreSQL connection-pool defaults.
    """
    url: str = _settings.database_url
    connect_args: dict[str, Any] = {}

    if url.startswith("sqlite"):
        # SQLite needs ``check_same_thread=False`` when used with FastAPI
        connect_args["check_same_thread"] = False
        engine = create_engine(
            url,
            connect_args=connect_args,
            echo=(_settings.app_env == "development"),
            pool_pre_ping=True,
        )

        # Enable WAL mode and foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn: Any, _connection_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    else:
        # PostgreSQL (or any other dialect)
        engine = create_engine(
            url,
            echo=(_settings.app_env == "development"),
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

    logger.info("Database engine created for %s", url.split("@")[-1] if "@" in url else url)
    return engine


engine: Engine = _build_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """Yield a database :class:`Session` and ensure it is closed afterwards.

    Intended for use as a FastAPI dependency::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables that do not yet exist.

    Idempotent — safe to call on every application startup.
    """
    logger.info("Initialising database tables …")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
