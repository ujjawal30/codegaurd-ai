# ── Stage 1: Base (system deps + Python deps) ──────────────────────
FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies needed by analysis tools & build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Install Python dependencies
RUN uv sync --frozen


# ── Stage 2: Development ───────────────────────────────────────────
FROM base AS development

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]


# ── Stage 3: Production ────────────────────────────────────────────
FROM python:3.14-slim AS production

WORKDIR /app

# Install only runtime system dependencies (no gcc / build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy pre-built virtual environment from base stage
COPY --from=base /opt/venv /opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_NO_CACHE=1

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Run as non-root user for security
RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
