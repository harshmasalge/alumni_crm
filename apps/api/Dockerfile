# Production image for Render (also used by local docker-compose).
# Push to GitHub -> Render rebuilds this Dockerfile and redeploys.
# Local dev overrides CMD via docker-compose (uvicorn --reload), so this
# file stays deploy-focused: install deps, copy code, migrate, serve.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# README.md is required: pyproject.toml declares it as the package readme,
# so `pip install -e .` fails without it being present at build time.
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

# Render injects $PORT; default keeps local `docker run` working.
# Migrations run on every deploy so a push carrying a new alembic
# revision upgrades the database before the new code serves traffic.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]