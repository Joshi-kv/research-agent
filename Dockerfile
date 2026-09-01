# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Install uv from the official distribution image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# uv: compile bytecode + copy (keep hardlinks/symlinks out of the layer)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Lock dependency definitions first for layer caching
COPY pyproject.toml uv.lock ./

# Install project deps into a dedicated venv (no source, no dev deps)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ ./src/

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

# System deps for binary packages (lxml, readability, trafilatura) at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy the venv + source from base (venv is self-contained, includes libs)
COPY --from=base /app/.venv /app/.venv
COPY --from=base --chown=app:app /app/src /app/src

USER app

EXPOSE 8000

# Support Render's $PORT or fall back to 8000. Production: 1 worker is enough
# for long-running SSE streams; keep it simple and predictable.
CMD ["sh", "-c", "uvicorn main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
