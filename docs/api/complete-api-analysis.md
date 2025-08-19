# API Analysis Template

**API Group/Module:** Core API
**Analyst:** ChatGPT
**Analysis Date:** 2025-08-19
**Files Analyzed:** `server/app.py`, `api/openapi.yaml`, `server/models.py`, `server/auth.py`, `tests/e2e/test_login_flow.py`, `design.md`

## API Overview

### Scope
- **Base Path:** `/` (OpenAPI spec uses `/api` prefix)
- **Design Specification:** `design.md` Section 6
- **OpenAPI Spec:** `api/openapi.yaml`
- **Purpose:** REST interface for conversation-driven state management and commit workflow.

### Authentication & Authorization
- **Authentication Method:** JWT bearer tokens issued at `/auth/login` and verified by dependency `get_current_user`【F:server/app.py†L181-L205】【F:server/auth.py†L203-L224】
- **Authorization Model:** Role and permission checks via `require_permission` and per-session access control【F:server/auth.py†L226-L250】
- **Design Compliance:** Design specifies RBAC in Section 7; implementation includes roles and permission lists but lacks explicit ABAC or field-level policies.
- **Security Implementation:** Tokens include `sub`, `email`, `role`; session-level access recorded in `session_permissions` table.

## Endpoint Analysis

### Endpoint: GET /sessions/{sid}/state
- **File Location:** `server/app.py:541-630`【F:server/app.py†L541-L630】
- **OpenAPI Reference:** `api/openapi.yaml` lines 9-30【F:api/openapi.yaml†L9-L30】
- **Design Specification:** `design.md` line 210【F:design.md†L210-L215】

#### Request Analysis
- **Parameters:**
  - Path: `sid`
  - Query: `paths` (comma-separated), `intent`, `slice_mode`
- **Validation:** checks session existence and supports context slicing.
- **Authentication Required:** Yes, via `get_current_user`.

#### Response Analysis
- **Success Responses:** 200 returns full or sliced state.
- **Error Responses:** 404 when session or state missing; 400 for invalid message, 500 etc. Format deviates from design's error spec (returns `{"detail": ...}`).

#### Implementation Status
- **Status:** ⚠️ Partial
- **Gaps Identified:** query params `intent` and `slice_mode` not documented in OpenAPI; error format non-standard.

### Endpoint: POST /sessions/{sid}/intents
- **File Location:** `server/app.py:652-699`【F:server/app.py†L652-L699】
- **OpenAPI Reference:** `api/openapi.yaml` lines 32-53【F:api/openapi.yaml†L32-L53】
- **Design Specification:** `design.md` line 211【F:design.md†L210-L215】

#### Request Analysis
- **Parameters:** Path `sid`; body `IntentionSet` model.
- **Validation:** schema validator; checks user write permission.
- **Authentication Required:** Yes.

#### Response Analysis
- **Success:** 200 with `intention_set_id`.
- **Error:** 403, 404, 422 with FastAPI default structure.

#### Implementation Status
- **Status:** ⚠️ Partial
- **Gaps Identified:** error format mismatch; OpenAPI spec lacks permission-related errors.

### Endpoint: POST /sessions/{sid}/patch-proposals
- **File Location:** `server/app.py:700-753`【F:server/app.py†L700-L753】
- **OpenAPI Reference:** `api/openapi.yaml` lines 55-76【F:api/openapi.yaml†L55-L76】
- **Design Specification:** `design.md` line 212【F:design.md†L210-L215】
- **Status:** ⚠️ Partial — implementation returns proposal with impact analysis, but openapi spec omits authentication and error cases.

### Endpoint: POST /sessions/{sid}/confirm?stage=
- **OpenAPI Reference:** unified endpoint lines 78-105【F:api/openapi.yaml†L78-L105】
- **Implementation:** server exposes three separate endpoints `/confirm-intent`, `/confirm-changes`, `/confirm-side-effects`【F:server/app.py†L1052-L1198】
- **Status:** ❌ Missing — spec and code diverge completely.

### Endpoint: POST /sessions/{sid}/commit
- **File Location:** `server/app.py:1324-1399`【F:server/app.py†L1324-L1399】
- **OpenAPI Reference:** `api/openapi.yaml` lines 107-128【F:api/openapi.yaml†L107-L128】
- **Status:** ⚠️ Partial — requires prior confirmations; error format non-standard.

### Endpoint: GET /sessions/{sid}/artifacts
- **File Location:** `server/app.py:1475-1504`【F:server/app.py†L1475-L1504】
- **OpenAPI Reference:** `api/openapi.yaml` lines 130-149【F:api/openapi.yaml†L130-L149】
- **Status:** ⚠️ Partial — response model lacks version field in spec; implementation includes `version` and `created_at`.

### Additional Implemented Endpoints
- `/auth/register`, `/auth/login`, `/auth/me`, `/sessions/{sid}/analyze`, `/sessions/{sid}/context-slices`, `/sessions`, `/health` etc., are not present in `openapi.yaml`.

## Data Model Compliance

### Request Models
#### Intention
- **File Location:** `server/models.py:38-86`【F:server/models.py†L38-L86】
- **OpenAPI Definition:** lines 162-176【F:api/openapi.yaml†L162-L176】
- **Implementation:** Enforces JSON Pointer format and action/value constraints.
- **Compliance Status:** ⚠️ Partial — OpenAPI lacks validators and enum enforcement details.

#### IntentionSet
- **File Location:** `server/models.py:88-107`【F:server/models.py†L88-L107】
- **OpenAPI Definition:** lines 177-185【F:api/openapi.yaml†L177-L185】
- **Compliance Status:** ✅ Compliant

### Response Models
#### State
- **File Location:** `server/models.py:308-330`【F:server/models.py†L308-L330】
- **OpenAPI Definition:** lines 151-161【F:api/openapi.yaml†L151-L161】
- **Compliance Status:** ✅ Compliant

#### PatchProposal / ImpactAnalysis
- **File Location:** `server/models.py:169-200` etc.【F:server/models.py†L169-L200】
- **OpenAPI Definition:** lines 193-259【F:api/openapi.yaml†L193-L259】
- **Compliance Status:** ⚠️ Partial — spec omits `stage_confirmations` and other fields returned by implementation.

## Error Handling Analysis

### Error Response Format
- **Standard Format:** FastAPI default `{"detail": ...}` (varies)
- **Design Requirement:** structured `error` object with `correlation_id`【F:design.md†L218-L228】
- **Compliance:** ❌ Non-compliant — no correlation IDs or standardized codes.
- **Missing Elements:** error codes, message structure, correlation IDs.

### Error Codes and Messages
- Implemented codes are mostly HTTP status with generic messages; design lists `VALIDATION_FAILED`, `CONFLICT`, `UNAUTHORIZED`, `NOT_FOUND`, `RATE_LIMIT`.
- Missing: mapping of codes to design spec, centralized error handler.

## Security Analysis

### Input Validation
- Schema validation for intentions and state; JSON Patch applied with error handling.

### Authentication & Authorization
- Token creation and verification with JWT secret key【F:server/auth.py†L95-L115】
- Permission checks via `require_permission`; session-based access recorded in DB【F:server/auth.py†L226-L250】
- Lacks rate limiting and advanced policy features mentioned in design.

### Security Vulnerabilities
- Error messages expose internal details; no account lockout or rate limiting; password stored as hash but no password policy.

## Testing Analysis

### API Testing
- **Test Files:** `tests/e2e/test_login_flow.py` exercises session state, intents, patch proposals, confirmations, commit, and conflict detection【F:tests/e2e/test_login_flow.py†L1-L287】
- **Test Coverage:** focuses on happy path and some conflict scenarios; authentication endpoints not tested.
- **Missing Tests:** error cases, auth failures, artifact retrieval.

## Gap Analysis

### Critical Gaps
1. **OpenAPI spec outdated**
   - **Impact:** tooling and client generation unreliable.
   - **Design Reference:** `design.md` Section 6
   - **Recommended Action:** regenerate `openapi.yaml` from current implementation; add auth endpoints.
2. **Error handling not standardized**
   - **Impact:** inconsistent client experience; harder debugging.
   - **Design Reference:** `design.md` Section 6.1
   - **Recommended Action:** implement global exception handler returning standard error format with correlation IDs.

### Medium Priority Gaps
- Split confirmation endpoints diverge from spec; need consolidation or spec update.
- Missing documentation for additional query parameters and response fields.

### Low Priority Gaps
- OpenAPI base path mismatch (`/api` vs `/`).
- Model definitions omit detailed field descriptions in spec.

## Recommendations

### Immediate Actions (0-2 weeks)
1. Align OpenAPI spec with implemented endpoints and authentication.
2. Add standardized error response middleware.

### Short-term Actions (2-8 weeks)
1. Expand test suite to cover auth failures and error paths.
2. Document and validate additional query parameters and fields.

### Long-term Actions (8+ weeks)
1. Implement rate limiting and more granular policy enforcement.
2. Introduce versioned API and deprecation strategy.

## Additional Notes

OpenAPI specification currently covers only a subset of implemented functionality; continuous synchronization is needed as the system evolves.

---

**Analysis Complete:** ✅ Yes
**Reviewed By:** _(pending review)_
**Review Date:** _(pending)_
