"""Unit tests for SQLite WAL engine, ORM models, and CRUD operations."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import select
from worker.db import (
    Base,
    DownloadJob,
    JobStateEnum,
    create_engine,
    verify_wal_mode,
)
from worker.magnetflix.v1 import pipeline_pb2


@pytest.fixture
async def temp_db():
    """Create a temporary SQLite database file with WAL pragmas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_magnetflix.sqlite3"
        db_url = f"sqlite+aiosqlite:///{db_path}"
        engine, session_factory = create_engine(db_url)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield session_factory, engine

        await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_wal_pragmas(temp_db):
    """Verify that SQLite engine automatically configures WAL mode and pragmas."""
    session_factory, _ = temp_db

    async with session_factory() as session:
        pragmas = await verify_wal_mode(session)

        assert pragmas["journal_mode"].lower() == "wal"
        assert pragmas["foreign_keys"] == 1
        assert pragmas["synchronous"] == 1  # 1 = NORMAL
        assert pragmas["busy_timeout"] == 5000


@pytest.mark.asyncio
async def test_download_job_crud(temp_db):
    """Test creating, reading, and updating a DownloadJob in SQLite."""
    session_factory, _ = temp_db

    # 1. Create Job
    job = DownloadJob(
        imdb_id="tt1375666",
        magnet_uri="magnet:?xt=urn:btih:dummy123",
        requested_by="alice",
    )

    async with session_factory() as session:
        session.add(job)
        await session.commit()
        job_id = job.id

    assert job_id is not None

    # 2. Read Job
    async with session_factory() as session:
        result = await session.execute(
            select(DownloadJob).where(DownloadJob.id == job_id)
        )
        saved = result.scalar_one()

        assert saved.imdb_id == "tt1375666"
        assert saved.magnet_uri == "magnet:?xt=urn:btih:dummy123"
        assert saved.requested_by == "alice"
        assert saved.state == JobStateEnum.QUEUED.value
        assert saved.progress_pct == 0.0
        assert saved.download_rate_bytes == 0
        assert saved.error_message == ""
        assert saved.title is None
        assert saved.year is None
        assert saved.created_at is not None
        assert saved.updated_at is not None
        assert saved.completed_at is None
        assert saved.is_terminal is False


@pytest.mark.asyncio
async def test_download_job_to_proto(temp_db):
    """Test converting a DownloadJob ORM model to a Protobuf JobStatus message."""
    session_factory, _ = temp_db

    job = DownloadJob(
        imdb_id="tt1375666",
        title="Inception",
        year=2010,
        magnet_uri="magnet:?xt=urn:btih:dummy123",
        requested_by="alice",
        progress_pct=42.5,
        download_rate_bytes=5242880,
    )

    async with session_factory() as session:
        session.add(job)
        await session.commit()

        proto = job.to_proto()
        assert isinstance(proto, pipeline_pb2.JobStatus)
        assert proto.job_id == job.id
        assert proto.imdb_id == "tt1375666"
        assert proto.title == "Inception"
        assert proto.year == 2010
        assert proto.requested_by == "alice"
        assert proto.state == pipeline_pb2.JOB_STATE_QUEUED
        assert abs(proto.progress_pct - 42.5) < 0.01
        assert proto.download_rate_bytes == 5242880
        assert proto.error_message == ""
        assert proto.created_at.seconds > 0


@pytest.mark.asyncio
async def test_download_job_state_transitions(temp_db):
    """Test state machine progression and terminal state invariants."""
    session_factory, _ = temp_db

    job = DownloadJob(
        imdb_id="tt0111161",
        magnet_uri="magnet:?xt=urn:btih:shawshank",
        requested_by="bob",
    )

    # 1. Valid Linear Progression:
    # QUEUED -> DOWNLOADING -> SCANNING -> VERIFYING_METADATA -> ORGANIZING -> COMPLETED
    job.transition_to(JobStateEnum.DOWNLOADING)
    assert job.state == JobStateEnum.DOWNLOADING.value
    assert job.completed_at is None

    job.transition_to(JobStateEnum.SCANNING)
    assert job.state == JobStateEnum.SCANNING.value

    job.transition_to(JobStateEnum.VERIFYING_METADATA)
    assert job.state == JobStateEnum.VERIFYING_METADATA.value

    job.transition_to(JobStateEnum.ORGANIZING)
    assert job.state == JobStateEnum.ORGANIZING.value

    job.transition_to(JobStateEnum.COMPLETED)
    assert job.state == JobStateEnum.COMPLETED.value
    assert job.is_terminal is True
    assert job.completed_at is not None

    # 2. Cannot transition out of terminal COMPLETED
    with pytest.raises(ValueError, match="Invalid state transition"):
        job.transition_to(JobStateEnum.DOWNLOADING)

    # 3. Direct failure transition from non-terminal state
    job_failing = DownloadJob(
        imdb_id="tt0068646",
        magnet_uri="magnet:?xt=urn:btih:godfather",
        requested_by="charlie",
    )
    job_failing.transition_to(
        JobStateEnum.FAILED, error_message="Tracker timed out"
    )
    assert job_failing.state == JobStateEnum.FAILED.value
    assert job_failing.error_message == "Tracker timed out"
    assert job_failing.is_terminal is True
    assert job_failing.completed_at is not None


@pytest.mark.asyncio
async def test_active_job_idempotency_query(temp_db):
    """Test querying active non-terminal jobs for duplicate rejection."""
    session_factory, _ = temp_db

    active_job = DownloadJob(
        imdb_id="tt1375666",
        magnet_uri="magnet:?xt=urn:btih:inception",
        requested_by="alice",
        state=JobStateEnum.DOWNLOADING.value,
    )
    completed_job = DownloadJob(
        imdb_id="tt0111161",
        magnet_uri="magnet:?xt=urn:btih:shawshank",
        requested_by="bob",
        state=JobStateEnum.COMPLETED.value,
    )

    async with session_factory() as session:
        session.add_all([active_job, completed_job])
        await session.commit()

        # Query for active job with tt1375666
        terminal_states = [JobStateEnum.COMPLETED.value, JobStateEnum.FAILED.value]
        stmt = (
            select(DownloadJob)
            .where(DownloadJob.imdb_id == "tt1375666")
            .where(DownloadJob.state.not_in(terminal_states))
        )
        res = await session.execute(stmt)
        found_active = res.scalar_one_or_none()
        assert found_active is not None
        assert found_active.id == active_job.id

        # Query for active job with tt0111161 (should be None because it's COMPLETED)
        stmt_comp = (
            select(DownloadJob)
            .where(DownloadJob.imdb_id == "tt0111161")
            .where(DownloadJob.state.not_in(terminal_states))
        )
        res_comp = await session.execute(stmt_comp)
        found_completed = res_comp.scalar_one_or_none()
        assert found_completed is None
