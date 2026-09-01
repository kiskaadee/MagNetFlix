FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY services/worker/pyproject.toml ./services/worker/
RUN uv sync --frozen --no-dev --package magnetflix-worker

COPY services/worker/src ./services/worker/src

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY services/worker/src ./services/worker/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/worker/src"

EXPOSE 50051
CMD ["python", "-m", "worker.main"]
