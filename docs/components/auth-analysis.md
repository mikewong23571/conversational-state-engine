# Component Analysis: Authentication System

**Component Name:** Authentication System
**Analyst:** ChatGPT
**Analysis Date:** 2025-08-19
**Files Analyzed:**
- `server/auth.py`
- `server/app.py`
- `tests/e2e/test_login_flow.py`
- `design.md` (Section 7)
- `pyproject.toml`

## Component Overview

### Purpose and Responsibility
- **Primary Function:** Provide user authentication, JWT issuance, and role-based permission checks.
- **Design Specification:** `design.md` Section 7 outlines RBAC roles (Admin/Reviewer/Editor/Viewer) and broader security policies.【F:design.md†L233-L239】
- **Actual Implementation:** Implements JWT-based auth with hard‑coded secret, basic role/permission mapping, and session access checks.【F:server/auth.py†L15-L18】【F:server/auth.py†L147-L152】【F:server/auth.py†L237-L257】

### Dependencies
- **Input Dependencies:** SQLite tables `users` and `session_permissions` for credential and access data.
- **Output Dependencies:** Authentication status and user context used by FastAPI endpoints like `/auth/login` and `/sessions/{sid}/analyze` for authorization decisions.【F:server/app.py†L162-L206】【F:server/app.py†L210-L220】
- **External Dependencies:** `python-jose` for JWT, `passlib[bcrypt]` for password hashing, `fastapi` for request handling.【F:pyproject.toml†L8-L15】

## Implementation Analysis

### Core Functionality

#### Function: `create_access_token`
- **File Location:** `server/auth.py:95-103`
- **Design Specification:** Generate time‑limited JWT tokens with secure signing.
- **Actual Implementation:** Encodes provided data with HS256 and configurable expiry; secret key is hard-coded.【F:server/auth.py†L95-L103】【F:server/auth.py†L15-L18】
- **Compliance Status:** ⚠️ Partial
- **Notes:** Hard-coded secret violates security best practices; no refresh-token support.

#### Function: `verify_token`
- **File Location:** `server/auth.py:105-114`
- **Design Specification:** Validate JWT signatures and expiration.
- **Actual Implementation:** Uses `jwt.decode` and raises HTTP 401 on failure.【F:server/auth.py†L105-L114】
- **Compliance Status:** ✅ Compliant
- **Notes:** Does not differentiate expiration vs. other errors.

#### Function: `authenticate_user`
- **File Location:** `server/auth.py:117-138`
- **Design Specification:** Verify credentials and return user context.
- **Actual Implementation:** Checks email, verifies bcrypt password, returns `User` model with permissions.【F:server/auth.py†L117-L138】
- **Compliance Status:** ✅ Compliant
- **Notes:** Lacks account lockout or rate limiting.

#### Function: `require_permission`
- **File Location:** `server/auth.py:226-235`
- **Design Specification:** Enforce role/permission checks per request.
- **Actual Implementation:** Dependency factory verifying permission membership, returns 403 on missing permission.【F:server/auth.py†L226-L235】
- **Compliance Status:** ✅ Compliant
- **Notes:** Permissions stored as strings; no hierarchy.

#### Function: `check_session_access`
- **File Location:** `server/auth.py:237-257`
- **Design Specification:** Restrict access to session resources.
- **Actual Implementation:** Admin bypass; otherwise checks `session_permissions` table.【F:server/auth.py†L237-L257】
- **Compliance Status:** ✅ Compliant
- **Notes:** Permission level (`read`/`write`) not enforced beyond presence.

### Data Models

#### Model: `User`
- **File Location:** `server/auth.py:26-31`
- **Design Specification:** Represent authenticated users with roles and permissions.
- **Actual Structure:** Contains `user_id`, `email`, `role`, `permissions` list.【F:server/auth.py†L26-L31】
- **Compliance Status:** ⚠️ Partial
- **Missing Fields:** No support for `Reviewer` or `Viewer` roles defined in design spec.

#### Model: `Token`
- **File Location:** `server/auth.py:42-44`
- **Design Specification:** Return access token and type to client.
- **Actual Structure:** `access_token` and `token_type` fields only.【F:server/auth.py†L42-L44】
- **Compliance Status:** ✅ Compliant
- **Extra Fields:** None

### Error Handling
- **Error Types Handled:** Credential errors raise HTTP 401; permission issues raise 403; user creation conflicts return 400.【F:server/auth.py†L105-L114】【F:server/auth.py†L226-L235】【F:server/auth.py†L161-L165】
- **Error Response Format:** Uses `HTTPException` with status codes and messages.
- **Design Compliance:** Partially aligns with general FastAPI error handling; design.md has no explicit section.
- **Missing Error Handling:** No differentiation for token expiration, missing tables, or brute‑force attempts.

### Performance Considerations
- **Observed Performance:** Synchronous SQLite queries for each request.
- **Design Targets:** None specified.
- **Bottlenecks Identified:** Password hashing with bcrypt may slow registration/login under load.
- **Optimization Opportunities:** Connection pooling or async database access.

## Testing Analysis

### Test Coverage
- **Test Files:** `tests/e2e/test_login_flow.py` covers login story flow but not authorization paths.【F:tests/e2e/test_login_flow.py†L1-L24】
- **Coverage Areas:** Session creation, intention flow; authentication invoked indirectly via endpoints.
- **Missing Tests:** No tests for `/auth/register`, token expiry, permission enforcement, or session access denial.
- **Test Quality:** Limited; lacks negative cases and security checks.

### Integration Testing
- **Integration Points Tested:** End-to-end workflow using HTTP requests; assumes running server.
- **Missing Integration Tests:** RBAC scenarios, invalid tokens, and session permission levels.

## Gap Analysis

### Critical Gaps (High Priority)
1. **Hard-coded JWT Secret**
   - **Impact:** Exposes system to token forging if source leaked.
   - **Recommended Action:** Load secret from environment variables or secret manager.
   - **Effort Estimate:** Small

2. **Incomplete Role Coverage**
   - **Impact:** Design-specified roles `Reviewer` and `Viewer` missing, limiting fine-grained access control.
   - **Recommended Action:** Implement full role set and mapping per design spec.
   - **Effort Estimate:** Medium

### Non-Critical Gaps (Medium/Low Priority)
1. **No Token Refresh Mechanism**
   - **Impact:** Users must re-login frequently; potential security risk if tokens never refreshed.
   - **Recommended Action:** Add refresh tokens or renewal endpoint.
   - **Effort Estimate:** Medium

2. **Limited Permission Levels**
   - **Impact:** `check_session_access` does not differentiate `read` vs `write` access.
   - **Recommended Action:** Enforce permission levels based on stored `permission_level`.
   - **Effort Estimate:** Medium

### Enhancement Opportunities
1. **Audit Logging**
   - **Benefit:** Traceability of auth actions per design requirement for auditing.
   - **Recommended Action:** Log login attempts, permission grants, and access checks.
   - **Effort Estimate:** Medium

## Code Quality Assessment

### Code Structure
- **Organization:** Auth logic centralized in `server/auth.py`; endpoints integrate cleanly via dependencies.
- **Naming Conventions:** Follows snake_case and Pydantic models; compliant with project standards.
- **Documentation:** Minimal docstrings; lacks high-level comments for security rationale.
- **Complexity:** Functions are straightforward; low cyclomatic complexity.

### Technical Debt
- **Identified Debt:** Hard-coded secrets, missing rate limiting, synchronous DB access.
- **Refactoring Needs:** Extract configuration, introduce service layer for users.
- **Code Smells:** Direct SQLite usage without abstraction.

## Security Analysis

### Security Considerations
- **Input Validation:** Relies on Pydantic models; email/password formats unchecked.
- **Authentication/Authorization:** JWT with role/permission checks; secret key not protected.【F:server/auth.py†L15-L18】
- **Data Protection:** Passwords hashed with bcrypt; tokens not stored server-side.
- **Vulnerabilities:** Hard-coded secret, missing rate limiting, broad CORS in app (allow `*`).【F:server/app.py†L38-L45】

## Configuration and Environment

### Configuration Requirements
- **Environment Variables:** Intended to load `SECRET_KEY` but currently hard-coded; CORS settings from app config.
- **Default Values:** Secret key default `"your-secret-key-change-in-production"` in code.【F:server/auth.py†L15-L18】
- **Configuration Validation:** None; missing checks for required env vars.

### Deployment Considerations
- **Deployment Requirements:** Ensure database and secret key initialized before startup.
- **Resource Requirements:** Minimal; SQLite and JWT operations lightweight.
- **Scaling Considerations:** Synchronous SQLite may become bottleneck at scale; consider external DB.

## Recommendations

### Immediate Actions (0-2 weeks)
1. Move `SECRET_KEY` and token settings to environment configuration; enforce permission levels (High, Small).
2. Add tests for `/auth/register` and permission enforcement (Medium, Small).

### Short-term Actions (2-8 weeks)
1. Implement full RBAC roles (`Admin/Reviewer/Editor/Viewer`) with hierarchical permissions (High, Medium).
2. Introduce refresh token support and token expiration tests (Medium, Medium).

### Long-term Actions (8+ weeks)
1. Add audit logging and ABAC/field-level controls per design spec (Medium, Large).
2. Migrate to async DB access and rate limiting for brute-force protection (Low, Large).

## Additional Notes
- Session permission levels stored but not enforced beyond existence; design suggests richer policy checks.

---

**Analysis Complete:** ✅ Yes
**Reviewed By:** N/A
**Review Date:** N/A
