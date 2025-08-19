# Project Maintenance Instructions

This document provides comprehensive instructions for maintaining the Conversational State Engine project.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Development Workflow](#development-workflow)
3. [Dependency Management](#dependency-management)
4. [Code Quality & Testing](#code-quality--testing)
5. [Database Management](#database-management)
6. [Troubleshooting](#troubleshooting)
7. [Release & Deployment](#release--deployment)
8. [Architecture Updates](#architecture-updates)

## Initial Setup

### Prerequisites

Ensure you have the required tools installed:

```bash
# Check if tools are installed
uv --version      # Python package manager
pnpm --version    # Node.js package manager
node --version    # Node.js runtime
```

### First-Time Setup

```bash
# Clone the repository
git clone <repository-url>
cd conversational-state-engine

# Run the setup script (handles everything)
./scripts/setup.sh
```

The setup script will:
- ✅ Verify prerequisites are installed
- ✅ Install Python dependencies via uv
- ✅ Install Node.js dependencies via pnpm workspace
- ✅ Initialize SQLite database
- ✅ Create .env configuration file

## Development Workflow

### Daily Development Commands

```bash
# Start development environment
pnpm run dev              # Both backend + frontend
pnpm run dev:backend      # Backend only (port 8000)
pnpm run dev:frontend     # Frontend only (port 5173)

# Individual service management
pnpm run server           # Alias for dev:backend
pnpm run client           # Alias for dev:frontend
pnpm start                # Alias for dev
```

### Development URLs

- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Code Quality Workflow

```bash
# Run all quality checks
pnpm run lint             # Lint all code
pnpm run type-check       # Type check all code
pnpm run test             # Run all tests

# Individual checks
pnpm run lint:backend     # ruff check server/
pnpm run lint:frontend    # eslint web/
pnpm run type-check:backend   # mypy server/
pnpm run type-check:frontend # tsc --noEmit

# Auto-fix issues
pnpm --filter web lint:fix    # Fix frontend linting issues
```

### Testing Workflow

```bash
# Backend tests (requires running server)
pnpm run test:backend         # Full test suite
pnpm run test:backend:quick   # Quick test run
uv run pytest tests/e2e/test_login_flow.py  # Specific test

# Test workflow
1. Start backend: pnpm run dev:backend
2. In another terminal: pnpm run test:backend
```

## Dependency Management

### Python Dependencies (Backend)

#### Adding Dependencies

```bash
# Add runtime dependency
echo 'new-package>=1.0.0' >> pyproject.toml  # Add to dependencies array
uv sync

# Add development dependency
echo 'dev-package>=1.0.0' >> pyproject.toml  # Add to [tool.uv] dev-dependencies
uv sync
```

#### Updating Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name@latest

# Check for outdated packages
uv tree
```

#### Dependency Structure

- **Runtime Dependencies**: In `[project.dependencies]`
- **Development Dependencies**: In `[tool.uv.dev-dependencies]`
- **Version Pinning**: Use `>=` for minimum versions, avoid exact pins unless necessary

### Node.js Dependencies (Frontend)

#### Adding Dependencies

```bash
# Add runtime dependency
pnpm --filter web add package-name

# Add development dependency  
pnpm --filter web add -D package-name

# Add to root (workspace management)
pnpm add -D package-name
```

#### Updating Dependencies

```bash
# Update all workspace dependencies
pnpm update

# Update specific workspace
pnpm --filter web update

# Check for outdated packages
pnpm outdated
```

#### Workspace Structure

- **Root package.json**: Workspace management, unified scripts
- **web/package.json**: Frontend-specific dependencies
- **pnpm-workspace.yaml**: Workspace configuration

## Code Quality & Testing

### Linting Configuration

#### Backend (Python)

- **Tool**: ruff
- **Config**: Built-in defaults
- **Command**: `pnpm run lint:backend`

Current issues to fix:
- 19 linting issues identified
- 15 auto-fixable with `ruff check --fix server/`
- Common issues: unused imports, bare except clauses

#### Frontend (TypeScript)

- **Tool**: eslint + TypeScript ESLint
- **Config**: `web/.eslintrc.json`
- **Command**: `pnpm run lint:frontend`
- **Auto-fix**: `pnpm --filter web lint:fix`

### Type Checking

#### Backend

```bash
# Type check Python code
pnpm run type-check:backend   # mypy server/

# Fix common issues:
# - Add type annotations to function parameters
# - Import types from typing module
# - Use proper return type hints
```

#### Frontend

```bash
# Type check TypeScript code
pnpm run type-check:frontend  # tsc --noEmit

# Build-time type checking
pnpm --filter web build       # Runs tsc && vite build
```

### Testing Strategy

#### End-to-End Tests

- **Location**: `tests/e2e/`
- **Framework**: pytest + requests
- **Test Server**: Must be running on http://localhost:8000

```bash
# Test workflow
1. pnpm run dev:backend       # Start server
2. pnpm run test:backend      # Run tests
```

#### Test Coverage

Current test scenarios:
- Complete login story workflow
- Conflict detection (authentication methods)
- Dependency priority validation
- Progressive confirmation stages
- Artifact generation verification

## Database Management

### Database Schema

The SQLite database (`state_engine.db`) includes:

- `sessions`: Conversation containers
- `states`: Versioned state snapshots
- `draft_intentions`: User intention drafts
- `patch_proposals`: Generated patches with impact analysis
- `commits`: Applied changes with rollback info
- `artifacts`: Generated outputs

### Database Operations

#### Reset Database

```bash
# Remove database file
rm state_engine.db

# Reinitialize
uv run python -c "from server.app import init_db; init_db()"
# Or restart development server (auto-initializes)
```

#### Backup Database

```bash
# Create backup
cp state_engine.db state_engine_backup_$(date +%Y%m%d).db

# Restore from backup
cp state_engine_backup_20231201.db state_engine.db
```

#### Database Migrations

Currently using SQLite with `CREATE TABLE IF NOT EXISTS`. For schema changes:

1. Update table definitions in `server/app.py` `init_db()` function
2. Consider data migration scripts for existing installations
3. Test with fresh database initialization

## Troubleshooting

### Common Issues

#### 1. Module Import Errors

**Error**: `ModuleNotFoundError: No module named 'models'`

**Solution**: Ensure relative imports in server modules
```python
# ❌ Wrong
from models import IntentionSet

# ✅ Correct  
from .models import IntentionSet
```

#### 2. Missing Dependencies

**Error**: `ModuleNotFoundError: No module named 'jinja2'`

**Solution**: Add missing dependency to pyproject.toml
```bash
# Add to [project.dependencies] array
uv sync
```

#### 3. PNPM Workspace Warnings

**Warning**: `The "workspaces" field in package.json is not supported`

**Solution**: Use `pnpm-workspace.yaml` instead of package.json workspaces field

#### 4. Port Already in Use

**Error**: `OSError: [Errno 98] Address already in use`

**Solution**: Kill existing processes
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn server.app:app --reload --port 8001
```

#### 5. Database Lock Issues

**Error**: `sqlite3.OperationalError: database is locked`

**Solution**: 
```bash
# Close all connections and restart server
pkill -f "uvicorn"
pnpm run dev:backend
```

#### 6. Build System Issues

**Error**: `Unable to determine which files to ship inside the wheel`

**Solution**: Ensure proper package structure
```toml
# In pyproject.toml
[tool.hatch.build.targets.wheel]
packages = ["server"]
```

### Logging and Debugging

#### Backend Debugging

```bash
# Enable debug logging
export UVICORN_LOG_LEVEL=debug
pnpm run dev:backend

# Check database contents
sqlite3 state_engine.db
.tables
.schema sessions
SELECT * FROM sessions LIMIT 5;
```

#### Frontend Debugging

```bash
# Development mode with source maps
pnpm run dev:frontend

# Check browser developer tools
# Network tab for API calls
# Console for JavaScript errors
```

### Performance Troubleshooting

#### Backend Performance

```bash
# Check server response time
curl -w "%{time_total}" http://localhost:8000/health

# Monitor database performance
sqlite3 state_engine.db
.timer on
SELECT COUNT(*) FROM sessions;
```

#### Frontend Performance

```bash
# Build analysis
pnpm --filter web build
# Check dist/ folder size

# Development server performance
# Check browser Network tab for slow requests
```

## Release & Deployment

### Version Management

#### Update Version

```bash
# Update version in both files
# 1. pyproject.toml
[project]
version = "0.2.0"

# 2. package.json (root)
"version": "0.2.0"

# 3. web/package.json
"version": "0.2.0"
```

#### Build for Production

```bash
# Build everything
pnpm run build

# Individual builds
pnpm run build:backend   # Python wheel
pnpm run build:frontend  # Static assets in web/dist/
```

### Deployment Preparation

#### Environment Configuration

```bash
# Production .env
CSE_DB_URL=postgresql://user:pass@host/db  # Use PostgreSQL for production
CSE_FEATURE_BATCH=true
CSE_LLM_PROVIDER=openai  # Configure actual LLM provider
```

#### Security Checklist

- [ ] Update CORS settings in `server/app.py`
- [ ] Remove debug flags
- [ ] Use production database (PostgreSQL recommended)
- [ ] Set up proper logging
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL certificates
- [ ] Environment variable validation

#### Deployment Commands

```bash
# Docker deployment (create Dockerfile)
FROM python:3.13-slim
COPY . /app
WORKDIR /app
RUN pip install uv && uv sync
CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Traditional deployment
uv build
pip install dist/*.whl
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### CI/CD Pipeline

#### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Lint
        run: pnpm run lint
      - name: Type check
        run: pnpm run type-check
      - name: Test
        run: |
          pnpm run dev:backend &
          sleep 5
          pnpm run test:backend
```

## Architecture Updates

### Design Document Compliance

**CRITICAL**: Always consult `design.md` before making architectural changes.

#### Design Change Process

1. **Review Impact**: Read relevant sections in `design.md`
2. **Document Changes**: Update `design.md` if modifying architecture
3. **Implementation**: Follow documented patterns and constraints
4. **Validation**: Ensure compliance with established requirements

### Common Architecture Tasks

#### Adding New API Endpoints

1. **Design Review**: Check `design.md` API contract section
2. **Model Updates**: Update `server/models.py` if needed
3. **Endpoint Implementation**: Add to `server/app.py`
4. **Database Schema**: Update `init_db()` if new tables needed
5. **Testing**: Add e2e tests in `tests/e2e/`

#### Adding New Conflict Rules

1. **Design Compliance**: Review `design.md` section 9
2. **Rule Implementation**: Add to `server/conflicts.py`
3. **Model Updates**: Update `ImpactAnalysis` if needed
4. **Testing**: Add test cases in `tests/e2e/test_login_flow.py`

#### Frontend Component Updates

1. **Component Design**: Follow existing patterns in `web/src/components/`
2. **Type Safety**: Maintain TypeScript interfaces
3. **State Management**: Keep UI state pure and typed
4. **Styling**: Use Tailwind CSS utility classes

### Package Structure Guidelines

```
conversational-state-engine/
├── server/                    # Python backend package
│   ├── __init__.py           # Package initialization
│   ├── app.py                # FastAPI application
│   ├── models.py             # Pydantic models
│   ├── conflicts.py          # Conflict detection
│   ├── analyzer.py           # Intent analysis
│   └── renderer_incremental.py # Artifact rendering
├── web/                       # Frontend workspace
│   ├── src/                  # React application
│   └── package.json          # Frontend dependencies
├── tests/e2e/                # End-to-end tests
├── scripts/                  # Development scripts
├── pyproject.toml            # Python project configuration
├── pnpm-workspace.yaml       # PNPM workspace configuration
├── package.json              # Root workspace management
└── design.md                 # Authoritative architecture
```

---

## Quick Reference

### Most Common Commands

```bash
# Daily development
./scripts/setup.sh           # First time only
pnpm run dev                 # Start development

# Quality assurance
pnpm run lint                # Check code quality
pnpm run test                # Run tests (server must be running)

# Dependency updates
uv sync --upgrade           # Update Python deps
pnpm update                 # Update Node.js deps

# Troubleshooting
rm state_engine.db && pnpm run dev:backend  # Reset database
pkill -f uvicorn            # Kill backend processes
```

### Support Resources

- **Architecture**: Read `design.md` for authoritative specifications
- **Development**: Check `CLAUDE.md` for Claude Code guidance
- **API Documentation**: http://localhost:8000/docs (when server running)
- **Issues**: Check linting output for immediate code improvements

---

*Last updated: 2024-01-XX*
*Project: Conversational State Engine v0.1.0*