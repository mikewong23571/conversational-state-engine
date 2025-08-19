# Repository Guidelines

## Project Structure & Module Organization
- `server/`: FastAPI backend. Entrypoint: `server/app.py`; domain models in `models.py`; conflict detection in `conflicts.py`; analyzers and renderers in `analyzer.py` and `renderer_incremental.py`. SQLite file `state_engine.db` is created at runtime.
- `api/`: OpenAPI spec (`openapi.yaml`).
- `web/`: Prototype React/TypeScript components and hooks under `src/`.
- `tests/`: End-to-end tests in `tests/e2e/` (pytest + requests).
- `design.md`: High-level design notes.

## Build, Test, and Development Commands
- Use uv (preferred): fast Python env/runner.
  - Install uv: `pipx install uv` (or see astral.sh/uv for other options).
  - Create env: `uv venv` (Python 3.10+). Activate: `source .venv/bin/activate` (optional).
  - Install deps: `uv pip install fastapi uvicorn[standard] pydantic jsonpatch pytest requests`.
  - Run API: `uv run uvicorn server.app:app --reload --port 8000` (docs at `/docs`).
  - Run e2e tests (server running): `uv run pytest -q tests/e2e`.
- Alternative (pip/venv): `python -m venv .venv && source .venv/bin/activate && pip install ...`.
- Example cURL: `curl -X POST http://localhost:8000/sessions` → returns `{ "session_id": ..., "version": "v1" }`.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indents, type hints. Modules/functions `snake_case`; classes `PascalCase`. Prefer Pydantic models for request/response schemas.
- TypeScript/React: Components `PascalCase` (`.tsx`), hooks `camelCase` in `web/src/hooks/` (`.ts`). Keep UI state pure and typed.
- JSON Patch paths follow RFC6901; ops: `add|remove|replace|move|copy|test`.

## Testing Guidelines
- Framework: `pytest`. E2E tests live under `tests/e2e/` and assume a running server at `http://localhost:8000` (adjust base path if you proxy under `/api`).
- Naming: `test_*.py`; test classes start with `Test*`.
- Practice: Focus on API flows (session → intents → proposals → confirm → commit). Add high-value scenarios (conflict detection, dependency order).

## Commit & Pull Request Guidelines
- Commits: Use concise, imperative messages. Conventional prefixes encouraged: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- PRs: Include scope/intent, linked issue, API changes, test plan (commands + expected results), and artifacts/screenshots for UI-related changes. Keep diffs focused and pass `pytest`.

## Security & Configuration Tips
- CORS is wide open for dev (`*`). Restrict `allow_origins` before production.
- SQLite is local and ephemeral; back up or reset by deleting `state_engine.db` during development. Use stronger auth and persistence in production.
