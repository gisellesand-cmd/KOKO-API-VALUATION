# syntax=docker/dockerfile:1.6
# Multi-stage build para KOKO Valuation API.
# Build context: raíz del repo (incluye api/, services/, db/, auth/).
#
# Recomendación: usar un .dockerignore en la raíz que excluya:
#   .git, .venv, __pycache__, *.pyc, tests/, *.md (excepto api/README.md), .env*

# ----- Stage 1: builder -----
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Preferimos requirements.txt; si en el futuro se migra a uv:
#   RUN pip install uv && uv sync --frozen
COPY requirements.txt* pyproject.toml* ./

RUN if [ -f requirements.txt ]; then \
        pip wheel --wheel-dir=/wheels -r requirements.txt ; \
    elif [ -f pyproject.toml ]; then \
        pip install --upgrade pip build && \
        pip wheel --wheel-dir=/wheels . ; \
    else \
        echo "Sin requirements.txt ni pyproject.toml; instalando set mínimo de FastAPI" && \
        pip wheel --wheel-dir=/wheels fastapi uvicorn[standard] pydantic ; \
    fi

# ----- Stage 2: runtime -----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    CORS_ORIGINS=*

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 koko

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copiamos el código completo del repo (api/, services/, db/, auth/).
# .dockerignore en la raíz mantiene la imagen liviana.
COPY . .

RUN chown -R koko:koko /app
USER koko

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
