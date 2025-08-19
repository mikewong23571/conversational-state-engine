# Toolchain & Commands Reference

This document provides a comprehensive reference for all tools, commands, and workflows used in the Conversational State Engine project.

## Table of Contents

1. [Tool Installation](#tool-installation)
2. [Workspace Management](#workspace-management)
3. [Python Backend Toolchain](#python-backend-toolchain)
4. [Frontend Toolchain](#frontend-toolchain)
5. [Development Commands](#development-commands)
6. [Quality Assurance Commands](#quality-assurance-commands)
7. [Testing Commands](#testing-commands)
8. [Build & Deployment Commands](#build--deployment-commands)
9. [Database Commands](#database-commands)
10. [Utility Scripts](#utility-scripts)
11. [Command Cheat Sheet](#command-cheat-sheet)

## Tool Installation

### Core Tools Required

#### 1. uv (Python Package Manager)
```bash
# Install uv (recommended method)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Alternative: pip install
pip install uv

# Alternative: pipx install
pipx install uv

# Verify installation
uv --version
```

#### 2. pnpm (Node.js Package Manager)
```bash
# Install pnpm (recommended method)
npm install -g pnpm

# Alternative: corepack
corepack enable
corepack prepare pnpm@latest --activate

# Verify installation
pnpm --version
```

#### 3. Node.js
```bash
# Install via Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
nvm use --lts

# Verify installation
node --version
npm --version
```

### Tool Verification
```bash
# Check all required tools
./scripts/setup.sh  # Includes prerequisite checking
```

## Workspace Management

### Project Structure
```
conversational-state-engine/          # Root workspace
├── package.json                      # Root workspace management
├── pnpm-workspace.yaml               # PNPM workspace configuration
├── pyproject.toml                    # Python project configuration
├── web/                              # Frontend workspace
│   └── package.json                  # Frontend dependencies
└── server/                           # Python backend package
```

### Workspace Configuration Files

#### Root package.json
```json
{
  "name": "conversational-state-engine",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "pnpm run /^dev:/",           # Parallel execution pattern
    "dev:backend": "uv run uvicorn server.app:app --reload --port 8000",
    "dev:frontend": "pnpm --filter web dev",
    "build": "pnpm run /^build:/",
    "test": "pnpm run /^test:/"
  }
}
```

#### pnpm-workspace.yaml
```yaml
packages:
  - 'web'
```

#### pyproject.toml
```toml
[project]
name = "conversational-state-engine"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "jsonpatch>=1.33",
    "requests>=2.31.0",
    "jinja2>=3.1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "mypy>=1.8.0",
    "ruff>=0.1.0",
]

[project.scripts]
cse-server = "server.app:main"
```

## Python Backend Toolchain

### uv Commands

#### Environment Management
```bash
# Create and sync environment
uv sync                               # Install all dependencies
uv sync --upgrade                     # Upgrade all dependencies
uv sync --dev                         # Install with dev dependencies (default)

# Environment info
uv tree                              # Show dependency tree
uv list                              # List installed packages
uv show package-name                 # Show package info
```

#### Dependency Management
```bash
# Add dependencies
uv add package-name                  # Add runtime dependency
uv add --dev package-name           # Add development dependency
uv add "package-name>=1.0.0"        # Add with version constraint

# Remove dependencies
uv remove package-name               # Remove dependency
uv remove --dev package-name         # Remove dev dependency

# Lock file management
uv lock                              # Generate/update lock file
uv lock --upgrade                    # Upgrade dependencies in lock
```

#### Running Commands
```bash
# Execute with uv
uv run python script.py              # Run Python script
uv run uvicorn server.app:app --reload  # Run server
uv run pytest tests/                 # Run tests
uv run mypy server/                  # Type checking
uv run ruff check server/            # Linting

# Using project scripts
uv run cse-server                    # Run server via project script
```

### Python Tools Configuration

#### Ruff (Linting & Formatting)
```bash
# Linting commands
uv run ruff check server/            # Check for issues
uv run ruff check --fix server/      # Auto-fix issues
uv run ruff check --unsafe-fixes server/  # Apply unsafe fixes

# Formatting commands
uv run ruff format server/           # Format code
```

#### MyPy (Type Checking)
```bash
# Type checking
uv run mypy server/                  # Check types
uv run mypy server/ --strict         # Strict type checking
uv run mypy server/ --show-error-codes  # Show error codes
```

#### Pytest (Testing)
```bash
# Test execution
uv run pytest                       # Run all tests
uv run pytest tests/e2e/            # Run specific directory
uv run pytest tests/e2e/test_login_flow.py  # Run specific file
uv run pytest -v                    # Verbose output
uv run pytest -q                    # Quiet output
uv run pytest --tb=short            # Short traceback format
```

## Frontend Toolchain

### pnpm Commands

#### Workspace Management
```bash
# Install dependencies
pnpm install                         # Install all workspace dependencies
pnpm --filter web install           # Install specific workspace
pnpm install --frozen-lockfile       # Install exact versions from lock

# Add dependencies
pnpm --filter web add package-name   # Add to specific workspace
pnpm --filter web add -D package-name  # Add dev dependency
pnpm add -D package-name             # Add to root workspace

# Update dependencies
pnpm update                          # Update all workspaces
pnpm --filter web update             # Update specific workspace
pnpm outdated                        # Check outdated packages
```

#### Workspace Filtering
```bash
# Filter commands
pnpm --filter web <command>          # Run command in web workspace
pnpm --filter "web*" <command>       # Pattern matching
pnpm --filter ./web <command>        # Path-based filtering
```

### Frontend Tools Configuration

#### Vite (Build Tool)
```bash
# Development server
cd web && pnpm dev                   # Start dev server (port 5173 or next available)
pnpm --filter web dev --port 3000    # Custom port
pnpm --filter web dev --host         # Expose to network

# Building
pnpm --filter web build              # Production build
pnpm --filter web preview            # Preview production build

# Vite configuration: web/vite.config.ts
```

#### ESLint (Linting)
```bash
# Linting commands
pnpm --filter web lint               # Check for issues
pnpm --filter web lint:fix           # Auto-fix issues
pnpm --filter web lint --ext ts,tsx  # Specify extensions
```

#### TypeScript Compiler
```bash
# Type checking
pnpm --filter web type-check         # Check types (no emit)
tsc --build web/                     # Build project references
```

#### Tailwind CSS
```bash
# Tailwind commands (via PostCSS)
pnpm --filter web build              # Processes Tailwind CSS
# Configuration: web/tailwind.config.js
# PostCSS: web/postcss.config.js
```

## Development Commands

### Project Setup
```bash
# First-time setup
./scripts/setup.sh                   # Complete project setup
./scripts/dev.sh                     # Development environment setup

# Manual setup steps
uv sync                               # Python dependencies
pnpm install                          # Node.js dependencies
```

### Development Servers
```bash
# Combined development
pnpm run dev                          # Start both backend + frontend
pnpm start                            # Alias for dev

# Individual services
pnpm run dev:backend                  # Backend only (port 8000)
pnpm run dev:frontend                 # Frontend only (port 5173+)
pnpm run server                       # Alias for dev:backend
pnpm run client                       # Alias for dev:frontend

# Direct commands
uv run uvicorn server.app:app --reload --port 8000  # Backend direct
pnpm --filter web dev                 # Frontend direct
```

### Service URLs
```bash
# Development URLs
http://localhost:8000                 # Backend API
http://localhost:5173                 # Frontend UI (or next available port)
http://localhost:8000/docs            # API Documentation (Swagger)
http://localhost:8000/health          # Health Check Endpoint
```

## Quality Assurance Commands

### Unified Quality Checks
```bash
# Run all quality checks
pnpm run lint                         # Lint all code
pnpm run type-check                   # Type check all code
pnpm run build                        # Build all projects

# Individual quality checks
pnpm run lint:backend                 # Python linting (ruff)
pnpm run lint:frontend                # TypeScript linting (eslint)
pnpm run type-check:backend           # Python type checking (mypy)
pnpm run type-check:frontend          # TypeScript checking (tsc)
```

### Backend Quality Assurance
```bash
# Linting
uv run ruff check server/             # Check issues
uv run ruff check --fix server/       # Auto-fix
uv run ruff format server/            # Format code

# Type checking
uv run mypy server/                   # Type check
uv run mypy server/ --install-types   # Install missing types

# Security checks (if configured)
uv run bandit -r server/              # Security linting
```

### Frontend Quality Assurance
```bash
# Linting
pnpm --filter web lint                # ESLint check
pnpm --filter web lint:fix            # Auto-fix issues

# Type checking
pnpm --filter web type-check          # TypeScript check

# Build validation
pnpm --filter web build               # Validate build
```

## Testing Commands

### Backend Testing
```bash
# Test execution (requires running server)
pnpm run test:backend                 # Full test suite
pnpm run test:backend:quick           # Quick test run (-q flag)

# Direct pytest commands
uv run pytest tests/e2e/              # All e2e tests
uv run pytest tests/e2e/test_login_flow.py  # Specific test
uv run pytest -v tests/e2e/           # Verbose output
uv run pytest -k "test_complete"      # Filter by name
uv run pytest --tb=short              # Short traceback
```

### Test Environment Setup
```bash
# Testing workflow
1. Terminal 1: pnpm run dev:backend   # Start server
2. Terminal 2: pnpm run test:backend  # Run tests
3. Wait for results

# Server health check before testing
curl http://localhost:8000/health     # Should return {"status": "healthy"}
```

### Frontend Testing
```bash
# Currently configured as placeholder
pnpm run test:frontend                # Returns "No tests specified"

# Future test commands (when implemented)
pnpm --filter web test                # Jest/Vitest tests
pnpm --filter web test:watch          # Watch mode
pnpm --filter web test:coverage       # Coverage report
```

## Build & Deployment Commands

### Building Projects
```bash
# Build all projects
pnpm run build                        # Build backend + frontend

# Individual builds
pnpm run build:backend                # Python wheel (uv build)
pnpm run build:frontend               # Static assets (tsc && vite build)

# Direct build commands
uv build                              # Python wheel in dist/
pnpm --filter web build               # Frontend in web/dist/
```

### Build Artifacts
```bash
# Backend build artifacts
dist/
├── conversational_state_engine-0.1.0-py3-none-any.whl
└── conversational_state_engine-0.1.0.tar.gz

# Frontend build artifacts
web/dist/
├── assets/
│   ├── index-[hash].js
│   └── index-[hash].css
└── index.html
```

### Deployment Preparation
```bash
# Production build validation
pnpm run build                        # Build all
pnpm run type-check                   # Verify types
pnpm run lint                         # Check code quality

# Server deployment
uv build                              # Create wheel
pip install dist/*.whl                # Install wheel
uvicorn server.app:app --host 0.0.0.0 --port 8000  # Run production

# Static file serving
# Serve web/dist/ with nginx/apache/CDN
```

## Database Commands

### Database Management
```bash
# Database initialization
uv run python -c "from server.app import init_db; init_db()"

# Database operations
sqlite3 state_engine.db               # Open database CLI
.tables                               # List tables
.schema sessions                      # Show table schema
SELECT COUNT(*) FROM sessions;        # Query data
.quit                                 # Exit
```

### Database Scripts
```bash
# Reset database
rm state_engine.db                    # Remove database file
pnpm run dev:backend                  # Restart server (auto-initializes)

# Backup database
cp state_engine.db backup_$(date +%Y%m%d_%H%M%S).db

# Restore database
cp backup_20231201_143022.db state_engine.db
```

## Utility Scripts

### Setup Scripts
```bash
# Complete setup
./scripts/setup.sh                   # First-time project setup
chmod +x scripts/*.sh                # Make scripts executable

# Development environment
./scripts/dev.sh                     # Development environment preparation
```

### Custom Scripts
```bash
# Add new utility scripts to scripts/
scripts/
├── setup.sh                         # Project setup
├── dev.sh                           # Development setup
├── backup.sh                        # Database backup (custom)
└── deploy.sh                        # Deployment script (custom)
```

### Environment Management
```bash
# Environment files
.env                                  # Environment configuration
.env.example                         # Example configuration

# Environment variables
export CSE_DB_URL="sqlite:///state_engine.db"
export CSE_FEATURE_BATCH="false"
export CSE_LLM_PROVIDER="mock"
```

## Command Cheat Sheet

### Daily Development
```bash
./scripts/setup.sh                   # First time only
pnpm run dev                          # Start development
pnpm run lint                         # Check code quality
pnpm run test                         # Run tests (server must be running)
```

### Quality Assurance
```bash
# Quick quality check
pnpm run lint && pnpm run type-check && pnpm run build

# Fix common issues
uv run ruff check --fix server/       # Fix Python linting
pnpm --filter web lint:fix            # Fix TypeScript linting
```

### Dependency Management
```bash
# Python dependencies
uv add package-name                   # Add Python package
uv sync --upgrade                     # Update all Python packages

# Node.js dependencies
pnpm --filter web add package-name    # Add frontend package
pnpm update                           # Update all Node.js packages
```

### Database Operations
```bash
# Reset database
rm state_engine.db && pnpm run dev:backend

# Query database
sqlite3 state_engine.db "SELECT * FROM sessions LIMIT 5;"
```

### Server Management
```bash
# Start servers
pnpm run dev:backend                  # Backend only
pnpm run dev:frontend                 # Frontend only
pnpm run dev                          # Both servers

# Stop servers
Ctrl+C                                # Stop current process
pkill -f "uvicorn"                    # Kill backend processes
pkill -f "vite"                       # Kill frontend processes
```

### Testing Workflow
```bash
# Complete test cycle
pnpm run dev:backend &                # Start server in background
sleep 5                               # Wait for server startup
pnpm run test:backend                 # Run tests
kill %1                               # Stop background server
```

### Build & Deploy
```bash
# Build for production
pnpm run build                        # Build everything
ls -la dist/ web/dist/                # Check build artifacts

# Deploy backend
pip install dist/*.whl                # Install Python package
uvicorn server.app:app --host 0.0.0.0  # Run production server
```

### Troubleshooting
```bash
# Check tool versions
uv --version && pnpm --version && node --version

# Check running processes
lsof -i :8000                         # Check port 8000
lsof -i :5173                         # Check port 5173

# Clean and restart
pnpm run clean                        # Clean build artifacts
rm -rf node_modules web/node_modules   # Remove node_modules
pnpm install                          # Reinstall dependencies
```

---

## Tool Documentation Links

- **uv**: https://docs.astral.sh/uv/
- **pnpm**: https://pnpm.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Vite**: https://vitejs.dev/
- **React**: https://react.dev/
- **Ruff**: https://docs.astral.sh/ruff/
- **MyPy**: https://mypy.readthedocs.io/
- **ESLint**: https://eslint.org/
- **Tailwind CSS**: https://tailwindcss.com/

---

*Generated for Conversational State Engine v0.1.0*
*Last updated: 2024-XX-XX*
