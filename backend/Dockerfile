FROM python:3.14-slim AS base

WORKDIR /app

# Install system dependencies needed by analysis tools
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

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
