FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY services/contracts ./services/contracts
COPY services/worker ./services/worker

# Synchronize dependencies for worker package
RUN uv sync --frozen --no-dev --package magnetflix-worker

# Final stage
FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

# Copy virtual environment and code
COPY --from=builder /app/.venv /app/.venv
COPY services/contracts/src ./services/contracts/src
COPY services/worker/src ./services/worker/src
COPY services/worker/alembic.ini ./alembic.ini
COPY services/worker/alembic ./alembic

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/worker/src:/app/services/contracts/src"

EXPOSE 50051
CMD ["python", "-m", "worker.main"]
