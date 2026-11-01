"""Unit and contract seam tests for generated Protobuf and gRPC stubs."""

from __future__ import annotations


def test_protobuf_and_grpc_stubs_importable():
    """Verify that both pipeline_pb2 and pipeline_pb2_grpc import cleanly."""
    from magnetflix.v1 import pipeline_pb2, pipeline_pb2_grpc

    assert pipeline_pb2.JOB_STATE_QUEUED == 1
    assert pipeline_pb2.JOB_STATE_DOWNLOADING == 2
    assert hasattr(pipeline_pb2_grpc, "PipelineServiceServicer")
    assert hasattr(pipeline_pb2_grpc, "PipelineServiceStub")


def test_proto_job_status_creation():
    """Verify that JobStatus protobuf message instantiates and serializes."""
    from google.protobuf.timestamp_pb2 import Timestamp
    from magnetflix.v1 import pipeline_pb2

    ts = Timestamp()
    ts.GetCurrentTime()

    status = pipeline_pb2.JobStatus(
        job_id="test-job-123",
        imdb_id="tt1375666",
        title="Inception",
        year=2010,
        requested_by="alice",
        state=pipeline_pb2.JOB_STATE_QUEUED,
        progress_pct=0.0,
        download_rate_bytes=0,
        error_message="",
        created_at=ts,
    )

    assert status.job_id == "test-job-123"
    assert status.title == "Inception"
    serialized = status.SerializeToString()
    assert len(serialized) > 0

    deserialized = pipeline_pb2.JobStatus()
    deserialized.ParseFromString(serialized)
    assert deserialized.imdb_id == "tt1375666"
