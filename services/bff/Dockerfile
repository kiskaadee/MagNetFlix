FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY services/contracts ./services/contracts
COPY services/bff ./services/bff

# Synchronize dependencies for bff package
RUN uv sync --frozen --no-dev --package magnetflix-bff

# Final stage
FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

# Copy virtual environment and code
COPY --from=builder /app/.venv /app/.venv
COPY services/contracts/src ./services/contracts/src
COPY services/bff/src ./services/bff/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/bff/src:/app/services/contracts/src"

EXPOSE 8000
CMD ["uvicorn", "bff.main:app", "--host", "0.0.0.0", "--port", "8000"]
