# Multi-stage Dockerfile for GeneNote Backend

# ========== Base Stage ==========
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY pyproject.toml poetry.lock* ./

# ========== Production Stage ==========
FROM base AS production

RUN poetry install --only main --no-root

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/
COPY pipeline/src/olymp_logo.pdf ./pipeline/src/olymp_logo.pdf

RUN poetry install --only main

RUN addgroup --system app && adduser --system --group app && \
    mkdir -p /data/files && chown -R app:app /data/files && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ========== Worker Stage (uses pre-built base with tools) ==========
# Worker stage requires pre-built worker-base image with bioinformatics tools
# Build it first: docker build -f Dockerfile.worker-base -t genenote-worker-base .
FROM genenote-worker-base:latest AS worker

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY src/ ./src/
COPY pipeline/ ./pipeline/
COPY scripts/ ./scripts/

RUN poetry install --only main

RUN addgroup --system app && adduser --system --group app && \
    mkdir -p /data/files && chown -R app:app /data/files && \
    mkdir -p /app/pipeline/results /app/pipeline/uploaded && \
    chown -R app:app /app

USER app

CMD ["python", "-m", "src.worker", "--mode", "pipeline"]