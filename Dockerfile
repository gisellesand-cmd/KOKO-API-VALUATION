# syntax=docker/dockerfile:1.6

# =========================================================
# Stage 1: builder
# Installs build dependencies and Python packages via uv.
# =========================================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build-time system dependencies (compilers + libpq headers for psycopg/asyncpg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install Python dependencies into the system site-packages so we can copy
# them into the slim runtime image in the next stage.
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# =========================================================
# Stage 2: runtime
# Slim image that runs the FastAPI app as a non-root user.
# =========================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Runtime system dependencies:
#   - libpq5: Postgres client library required by psycopg/asyncpg at runtime
#   - curl: used by the container HEALTHCHECK below
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user `koko` with uid 1000
RUN groupadd --system --gid 1000 koko \
    && useradd --system --uid 1000 --gid koko --create-home --shell /bin/bash koko

# Copy installed Python packages and console scripts from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy application source code with correct ownership
COPY --chown=koko:koko . /app

USER koko

EXPOSE 8080

# Container-level health check hits the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
