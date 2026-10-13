"""Database module for MagNetFlix worker service."""

from worker.db.engine import (
    DEFAULT_DATABASE_URL,
    configure_sqlite_pragmas,
    create_engine,
    get_db_session,
    get_engine,
    get_session_factory,
    normalize_database_url,
    verify_wal_mode,
)
from worker.db.models import (
    ALLOWED_TRANSITIONS,
    Base,
    DownloadJob,
    JobStateEnum,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "Base",
    "DEFAULT_DATABASE_URL",
    "DownloadJob",
    "JobStateEnum",
    "configure_sqlite_pragmas",
    "create_engine",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "normalize_database_url",
    "verify_wal_mode",
]
