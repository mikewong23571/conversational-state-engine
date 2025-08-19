# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Conversational State Engine (CSE)** - an LLM-driven state maintenance system that translates user requirements into auditable JSON Patch operations through conversational interfaces. The system maintains a single source of truth with versioning, conflict detection, and artifact generation.

## Architecture

The system follows a **对话 → 意图 → Patch → 渐进式确认 → Commit → Artifact** pipeline:

- **FastAPI Backend** (`server/`): Core API with state management, conflict detection, and incremental rendering
- **SQLite Database**: Stores sessions, states, intentions, patches, commits, and artifacts
- **React/TypeScript Frontend** (`web/src/`): Prototype components for UI interaction
- **OpenAPI Specification** (`api/openapi.yaml`): Complete API contract

**Authoritative Design**: See `design.md` for the complete architectural specification and implementation requirements. This document is the single source of truth for all design decisions.

**Project Documentation**:
- `toolchain.md` - Comprehensive reference for all tools, commands, and workflows
- `instructions.md` - Complete project maintenance and development guidelines
- `design.md` - Authoritative architectural specifications

### Core Components

- **Dialogue Analyzer**: Parses natural language and command inputs into structured intentions
- **Patch Planner**: Converts intentions to RFC6902 JSON patches
- **Impact Analyzer**: Detects structural conflicts and logical rule violations
- **Confirm Engine**: Progressive confirmation workflow (intent → change → side-effect)
- **Versioned State Store**: Atomic commits with rollback capability
- **Incremental Renderer**: Generates artifacts (Markdown, CSV) with caching

## Development Commands

> **📚 Complete Reference**: See `toolchain.md` for comprehensive command documentation and `instructions.md` for detailed maintenance procedures.

### Quick Start
```bash
# First time setup
./scripts/setup.sh

# Daily development
pnpm run dev          # Start both backend and frontend
pnpm run dev:backend  # Backend only (http://localhost:8000)
pnpm run dev:frontend # Frontend only (http://localhost:5173)
```

### Workspace Management (Root Level)
```bash
# Setup project from scratch
./scripts/setup.sh

# Install all dependencies
pnpm run setup

# Development (runs both servers)
pnpm run dev
pnpm start            # alias for dev

# Build everything
pnpm run build

# Test everything
pnpm run test

# Lint everything
pnpm run lint

# Type check everything  
pnpm run type-check

# Clean build artifacts
pnpm run clean
```

### Backend Only (using uv)
```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn server.app:app --reload --port 8000

# Run via project script
uv run cse-server

# Run tests (server must be running)
uv run pytest tests/e2e/ -v
uv run pytest tests/e2e/test_login_flow.py  # specific test
uv run pytest tests/e2e/ -q                 # quiet mode
```

### Frontend Only (using pnpm)
```bash
# Navigate to web directory
cd web

# Install dependencies
pnpm install

# Development server (http://localhost:5173)
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm type-check

# Linting
pnpm lint
pnpm lint:fix    # auto-fix issues

# Preview production build
pnpm preview
```

### API Usage
```bash
# Create new session
curl -X POST http://localhost:8000/sessions

# Get session state
curl http://localhost:8000/sessions/{session_id}/state

# Health check
curl http://localhost:8000/health

# API documentation available at
http://localhost:8000/docs
```

## Code Conventions

### Python (Backend)
- **Style**: PEP 8, 4-space indentation, type hints required
- **Naming**: `snake_case` for modules/functions, `PascalCase` for classes
- **Models**: Use Pydantic for request/response schemas
- **Database**: SQLite with connection context managers
- **Patches**: RFC6902 JSON Patch standard for state mutations

### TypeScript/React (Frontend)
- **Components**: `PascalCase` (.tsx files)
- **Hooks**: `camelCase` in `web/src/hooks/` (.ts files)
- **State Management**: Keep UI state pure and typed
- **Build Tool**: Vite with TypeScript compilation
- **Styling**: Tailwind CSS for utility-first styling

### API Design
- **Endpoints**: RESTful with `/sessions/{sid}/` prefix
- **State Operations**: Support path slicing with RFC6901 pointers
- **Error Responses**: Standardized format with correlation IDs

## Key Data Models

### Core Entities
- **Session**: Conversation container with versioned state
- **Intention**: Structured user intent (action/target_path/value/reason/confidence)
- **Patch**: RFC6902 operations for state modification
- **Commit**: Atomic state changes with reverse patches for rollback
- **Artifact**: Rendered outputs (Markdown, CSV, etc.)

### State Structure
```json
{
  "version": "v1",
  "schema_version": "1.0.0", 
  "data": {
    "stories": [...],
    "glossary": [...]
  }
}
```

## Conflict Detection Rules

The system detects both structural and logical conflicts:

- **Authentication Method Conflict**: `auth_type=SSO` conflicts with local password requirements
- **Dependency Order**: Dependencies must have equal or higher priority than dependents
- **Timeline Consistency**: `end_date` must be after `start_date`
- **Structural Conflicts**: Path existence, type validation, reference integrity

## Testing Approach

### End-to-End Tests
- **Location**: `tests/e2e/`
- **Framework**: pytest + requests
- **Coverage**: Complete flows from intention to artifact generation
- **Server Requirement**: Tests expect running server at `http://localhost:8000`

### Test Scenarios
- Complete login story workflow
- Conflict detection (authentication methods)
- Dependency priority validation
- Progressive confirmation stages
- Artifact generation verification

## Database Schema

The SQLite database includes tables for:
- `sessions`: Conversation containers
- `states`: Versioned state snapshots
- `draft_intentions`: User intention drafts
- `patch_proposals`: Generated patches with impact analysis
- `commits`: Applied changes with rollback info
- `artifacts`: Generated outputs

## Configuration

### Environment Variables
- `CSE_DB_URL`: Database connection string (default: sqlite:///state_engine.db)
- `CSE_FEATURE_BATCH`: Enable batch intention processing
- `CSE_LLM_PROVIDER`: LLM provider (mock/openai/vllm)

### CORS Configuration
Currently open for development (`*`). Restrict `allow_origins` for production.

## Important Implementation Notes

### Documentation Hierarchy
1. **`design.md`** - Authoritative architectural specifications (MUST follow)
2. **`instructions.md`** - Complete project maintenance and development procedures  
3. **`toolchain.md`** - Comprehensive command reference and tool documentation
4. **`CLAUDE.md`** - Claude Code guidance (this file)

### Design Compliance Requirements
**STRICTLY follow the design specifications in `design.md`**. This document contains the authoritative architectural guidance for the Conversational State Engine.

### Core Design Principles
- **State Immutability**: States are versioned and never modified in-place
- **Atomic Operations**: All patches are applied in transactions with rollback capability
- **Incremental Rendering**: Artifacts are generated incrementally with fragment caching
- **Progressive Confirmation**: Three-stage confirmation prevents unintended changes
- **Conflict Resolution**: Automatic suggestions provided for detected conflicts
- **Tool Management**: Use `uv` for Python environment management and `pnpm` for frontend package management
- **Workspace Setup**: Run `./scripts/setup.sh` for initial project setup
- **Unified Development**: Use root-level `pnpm` commands for managing both backend and frontend

### Design Document References
The `design.md` file contains detailed specifications for:
- Complete pipeline architecture: 对话 → 意图 → Patch → 渐进式确认 → Commit → Artifact
- Component responsibilities and data models
- Database schema and indexing strategies
- Conflict detection rules and impact analysis
- API contract and error handling standards
- Security and compliance requirements
- Performance targets and optimization strategies

**All implementation decisions must align with the design document.** When adding new features or modifying existing functionality, first consult `design.md` to ensure compliance with the established architecture.

## Common Development Patterns

### Design-First Development
**Always consult `design.md` before implementing new features:**
1. Review the relevant sections in `design.md` for specifications
2. Ensure compliance with established patterns and constraints
3. Update the design document if introducing significant architectural changes
4. Implement according to the documented requirements

**For detailed procedures, see `instructions.md` section "Architecture Updates".**

### Adding New Conflict Rules
1. Consult `design.md` section 9 for conflict detection specifications
2. Add rule detection logic in `server/conflicts.py`
3. Update `ImpactAnalysis` model if new conflict types needed
4. Add test cases in `tests/e2e/test_login_flow.py`

*Complete procedure in `instructions.md` > "Architecture Updates" > "Adding New Conflict Rules"*

### Extending Artifact Types
1. Review `design.md` section 4.7 for rendering requirements
2. Create new renderer in `server/renderer_incremental.py`
3. Add rendering logic in commit endpoint (`server/app.py`)
4. Update artifact storage and retrieval

*Complete procedure in `instructions.md` > "Architecture Updates" > "Extending Artifact Types"*

### Adding New Intent Actions
1. Check `design.md` section 4.1 for intention specifications
2. Update `Action` enum in `server/models.py`
3. Add action handling in patch planning logic
4. Update command parsing if applicable

*Complete procedure in `instructions.md` > "Architecture Updates" > "Adding New API Endpoints"*

## Additional Resources

### Command References
- **All Commands**: See `toolchain.md` for comprehensive command documentation
- **Development Workflow**: See `instructions.md` for complete procedures
- **Quick Commands**: Use the cheat sheet in `toolchain.md`

### Troubleshooting
- **Common Issues**: See `instructions.md` > "Troubleshooting" section
- **Tool Problems**: See `toolchain.md` > "Troubleshooting" section  
- **Architecture Issues**: Consult `design.md` for specifications

### Maintenance
- **Project Setup**: `./scripts/setup.sh` or see `instructions.md` > "Initial Setup"
- **Dependency Updates**: See `instructions.md` > "Dependency Management"
- **Quality Assurance**: See `instructions.md` > "Code Quality & Testing"

## LLM Provider Configuration

The system supports multiple LLM providers through OpenAI-compatible APIs:

### Available Providers
- **OpenAI**: Official API (set `CSE_LLM_PROVIDER=openai`)
- **vLLM**: Local inference server (set `CSE_LLM_PROVIDER=openai` with `CSE_API_BASE_URL`)
- **Ollama**: Local models (set `CSE_LLM_PROVIDER=openai` with `CSE_API_BASE_URL`)
- **DeepSeek**: DeepSeek API (set `CSE_LLM_PROVIDER=openai` with `CSE_API_BASE_URL`)
- **Mock**: For development/testing (set `CSE_LLM_PROVIDER=mock`)

### Configuration Examples
```bash
# OpenAI
CSE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key

# vLLM Local Server
CSE_LLM_PROVIDER=openai
CSE_API_BASE_URL=http://localhost:8000/v1
CSE_API_KEY=dummy-key

# Ollama
CSE_LLM_PROVIDER=openai
CSE_API_BASE_URL=http://localhost:11434/v1
CSE_MODEL=llama2
```

**Complete setup guide**: See `OPENAI_SETUP.md` for detailed configuration instructions.

## Current Implementation Status

### Frontend Gaps (from gap.md)
The current frontend implementation has significant gaps compared to the design specifications:

1. **Missing Progressive Confirmation**: Design requires 3-stage confirmation (Intent → Change → Side-Effect), but current implementation only has single-step confirmation
2. **Incomplete Command Channel**: Design expects structured command syntax (`/add`, `/edit`, `/del`, `/set`) but parsing is not implemented
3. **Disabled Commit Flow**: Commit functionality is currently disabled in `web/src/App.tsx:370-372`

### Key Files to Understand
- `server/app.py`: Main FastAPI application with all endpoints
- `server/models.py`: Pydantic models and data structures
- `server/conflicts.py`: Conflict detection logic
- `server/analyzer.py`: Intent analysis (Mock vs LLM)
- `api/openapi.yaml`: Complete API specification
- `design.md`: Authoritative architectural guidance
- `gap.md`: Current implementation gaps analysis