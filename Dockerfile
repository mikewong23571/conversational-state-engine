FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN pip install uv && uv pip install --system -e .[dev]
COPY . /app
CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
