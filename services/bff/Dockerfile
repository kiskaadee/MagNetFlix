FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY services/bff/pyproject.toml ./services/bff/
RUN uv sync --frozen --no-dev --package magnetflix-bff

COPY services/bff/src ./services/bff/src

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY services/bff/src ./services/bff/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/services/bff/src"

EXPOSE 8000
CMD ["uvicorn", "bff.main:app", "--host", "0.0.0.0", "--port", "8000"]
