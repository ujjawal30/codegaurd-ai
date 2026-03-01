FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

RUN pip install uv
RUN uv sync --frozen

COPY . .

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
