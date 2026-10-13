"""SQLAlchemy async database engine and session management with SQLite WAL mode."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///data/magnetflix.sqlite3"


def normalize_database_url(url: str | None = None) -> str:
    """Normalize database URL to use async aiosqlite driver for SQLite.

    If given 'sqlite:////path', converts to 'sqlite+aiosqlite:////path'.
    """
    raw_url = url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    if raw_url.startswith("sqlite://") and not raw_url.startswith("sqlite+aiosqlite://"):
        return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return raw_url


def _ensure_sqlite_parent_dir(db_url: str) -> None:
    """Ensure parent directory exists for file-based SQLite database."""
    if not db_url.startswith("sqlite"):
        return
    prefix = "sqlite+aiosqlite:///"
    if db_url.startswith(prefix):
        raw_path = db_url[len(prefix) :]
        if raw_path and raw_path != ":memory:":
            db_file = Path(raw_path).resolve()
            db_file.parent.mkdir(parents=True, exist_ok=True)


def configure_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Register SQLite PRAGMAs for WAL mode, foreign keys, and synchronous=NORMAL."""

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()


def create_engine(
    url: str | None = None, echo: bool = False
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an AsyncEngine and async sessionmaker configured with WAL pragmas."""
    normalized_url = normalize_database_url(url)
    _ensure_sqlite_parent_dir(normalized_url)

    engine = create_async_engine(
        normalized_url,
        echo=echo,
        future=True,
    )

    if normalized_url.startswith("sqlite"):
        configure_sqlite_pragmas(engine)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return engine, session_factory


# Module-level default singleton engine and sessionmaker
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the global AsyncEngine instance."""
    global _engine, _session_factory
    if _engine is None:
        _engine, _session_factory = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the global async_sessionmaker instance."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine, _session_factory = create_engine()
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session context."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def verify_wal_mode(session: AsyncSession) -> dict[str, Any]:
    """Inspect and return active SQLite pragmas.

    Queries journal_mode, foreign_keys, synchronous, and busy_timeout.
    """
    jm_res = await session.execute(text("PRAGMA journal_mode;"))
    fk_res = await session.execute(text("PRAGMA foreign_keys;"))
    sync_res = await session.execute(text("PRAGMA synchronous;"))
    busy_res = await session.execute(text("PRAGMA busy_timeout;"))

    return {
        "journal_mode": jm_res.scalar(),
        "foreign_keys": fk_res.scalar(),
        "synchronous": sync_res.scalar(),
        "busy_timeout": busy_res.scalar(),
    }
