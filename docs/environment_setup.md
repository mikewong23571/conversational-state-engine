# Development Environment Setup

## Using Docker Compose
1. Ensure Docker is installed.
2. Run `docker-compose up --build`.
3. Access the API at `http://localhost:8000`.

## Local Setup
1. Install [uv](https://github.com/astral-sh/uv).
2. Create a virtual environment: `uv venv`.
3. Install dependencies: `uv pip install -e .[dev]`.
4. Start the server: `uv run uvicorn server.app:app --reload`.

## Troubleshooting
- Port 8000 already in use: stop the conflicting process or change the port.
- Missing dependencies: run `uv pip install -e .[dev]` again.
- Database issues: delete `state_engine.db` and rerun `scripts/seed_db.py`.
