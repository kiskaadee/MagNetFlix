"""SQLAlchemy ORM models for MagNetFlix download jobs and audit trail."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from google.protobuf.timestamp_pb2 import Timestamp
from magnetflix.v1 import pipeline_pb2
from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy ORM models."""

    pass


class JobStateEnum(str, Enum):
    """Enumeration of valid lifecycle states for a download job."""

    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    SCANNING = "SCANNING"
    VERIFYING_METADATA = "VERIFYING_METADATA"
    ORGANIZING = "ORGANIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid forward state transitions in the pipeline
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    JobStateEnum.QUEUED.value: {
        JobStateEnum.DOWNLOADING.value,
        JobStateEnum.FAILED.value,
    },
    JobStateEnum.DOWNLOADING.value: {
        JobStateEnum.SCANNING.value,
        JobStateEnum.FAILED.value,
    },
    JobStateEnum.SCANNING.value: {
        JobStateEnum.VERIFYING_METADATA.value,
        JobStateEnum.FAILED.value,
    },
    JobStateEnum.VERIFYING_METADATA.value: {
        JobStateEnum.ORGANIZING.value,
        JobStateEnum.FAILED.value,
    },
    JobStateEnum.ORGANIZING.value: {
        JobStateEnum.COMPLETED.value,
        JobStateEnum.FAILED.value,
    },
    JobStateEnum.COMPLETED.value: set(),
    JobStateEnum.FAILED.value: set(),
}

PROTO_STATE_MAP = {
    JobStateEnum.QUEUED.value: pipeline_pb2.JOB_STATE_QUEUED,
    JobStateEnum.DOWNLOADING.value: pipeline_pb2.JOB_STATE_DOWNLOADING,
    JobStateEnum.SCANNING.value: pipeline_pb2.JOB_STATE_SCANNING,
    JobStateEnum.VERIFYING_METADATA.value: pipeline_pb2.JOB_STATE_VERIFYING_METADATA,
    JobStateEnum.ORGANIZING.value: pipeline_pb2.JOB_STATE_ORGANIZING,
    JobStateEnum.COMPLETED.value: pipeline_pb2.JOB_STATE_COMPLETED,
    JobStateEnum.FAILED.value: pipeline_pb2.JOB_STATE_FAILED,
}


def _datetime_to_timestamp(dt: datetime | None) -> Timestamp:
    """Convert Python datetime to Google Protobuf Timestamp."""
    ts = Timestamp()
    if dt is not None:
        ts.FromDatetime(dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))
    return ts


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


def extract_info_hash(magnet_uri: str) -> str | None:
    """Extract and lowercase the BTIH info-hash from a BitTorrent magnet URI."""
    match = re.search(r"urn:btih:([a-zA-Z0-9]+)", magnet_uri, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


class DownloadJob(Base):
    """ORM model representing an acquisition and relocation pipeline job."""

    __tablename__ = "download_jobs"
    __table_args__ = (
        Index(
            "uq_download_jobs_active_imdb_id",
            "imdb_id",
            unique=True,
            sqlite_where=text("state NOT IN ('COMPLETED', 'FAILED')"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique UUID primary key",
    )
    imdb_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="IMDb identifier (e.g. tt1375666)",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Canonical movie title resolved from TMDB",
    )
    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Release year resolved from TMDB",
    )
    magnet_uri: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="BitTorrent magnet URI",
    )
    info_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="BitTorrent info-hash extracted from magnet URI",
    )
    requested_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        doc="Authenticated user from Remote-User SSO header",
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStateEnum.QUEUED.value,
        index=True,
        doc="Current pipeline lifecycle state",
    )
    progress_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Download progress percentage (0.0 to 100.0)",
    )
    download_rate_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        doc="Download rate in bytes/sec",
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="Terminal error description if state is FAILED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        doc="UTC timestamp when job was enqueued",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        doc="UTC timestamp when job status was last updated",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when job transitioned to terminal COMPLETED or FAILED",
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize DownloadJob with default field values."""
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "state" not in kwargs:
            kwargs["state"] = JobStateEnum.QUEUED.value
        if "progress_pct" not in kwargs:
            kwargs["progress_pct"] = 0.0
        if "download_rate_bytes" not in kwargs:
            kwargs["download_rate_bytes"] = 0
        if "error_message" not in kwargs:
            kwargs["error_message"] = ""
        if "created_at" not in kwargs:
            kwargs["created_at"] = utc_now()
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = utc_now()
        if "info_hash" not in kwargs or kwargs["info_hash"] is None:
            if "magnet_uri" in kwargs and kwargs["magnet_uri"]:
                kwargs["info_hash"] = extract_info_hash(kwargs["magnet_uri"])
        elif isinstance(kwargs.get("info_hash"), str):
            kwargs["info_hash"] = kwargs["info_hash"].lower()
        super().__init__(**kwargs)

    @property
    def is_terminal(self) -> bool:
        """Return True if the job is in a terminal state (COMPLETED or FAILED)."""
        return self.state in (JobStateEnum.COMPLETED.value, JobStateEnum.FAILED.value)

    def transition_to(
        self,
        new_state: JobStateEnum | str,
        error_message: str | None = None,
    ) -> None:
        """Safely transition job state following the state machine invariants.

        Raises:
            ValueError: If the requested state transition is invalid.
        """
        target = new_state.value if isinstance(new_state, JobStateEnum) else new_state
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())

        if target not in allowed:
            raise ValueError(
                f"Invalid state transition from '{self.state}' to '{target}'. "
                f"Allowed transitions: {allowed}"
            )

        self.state = target
        self.updated_at = utc_now()

        if error_message is not None:
            self.error_message = error_message

        if self.is_terminal and self.completed_at is None:
            self.completed_at = utc_now()

    def to_proto(self) -> pipeline_pb2.JobStatus:
        """Convert ORM model instance into a Protobuf JobStatus message."""
        proto_state = PROTO_STATE_MAP.get(
            self.state, pipeline_pb2.JOB_STATE_UNSPECIFIED
        )

        return pipeline_pb2.JobStatus(
            job_id=self.id,
            imdb_id=self.imdb_id,
            title=self.title or "",
            year=self.year or 0,
            requested_by=self.requested_by,
            state=proto_state,
            progress_pct=self.progress_pct,
            download_rate_bytes=self.download_rate_bytes,
            error_message=self.error_message,
            created_at=_datetime_to_timestamp(self.created_at),
            updated_at=_datetime_to_timestamp(self.updated_at),
            completed_at=_datetime_to_timestamp(self.completed_at),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "id": self.id,
            "imdb_id": self.imdb_id,
            "title": self.title,
            "year": self.year,
            "magnet_uri": self.magnet_uri,
            "info_hash": self.info_hash,
            "requested_by": self.requested_by,
            "state": self.state,
            "progress_pct": self.progress_pct,
            "download_rate_bytes": self.download_rate_bytes,
            "error_message": self.error_message,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
