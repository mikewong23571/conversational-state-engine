# Progressive Confirmation Design Gap Analysis

**Analysis Area:** Progressive Confirmation
**Analyst:** ChatGPT
**Analysis Date:** 2025-08-19
**Design Document Version:** Current

## Analysis Scope

### Design Sections Analyzed
- **Primary Section:** design.md §4.5 Confirm Engine; §10 Progressive confirmation state machine
- **Related Sections:** gap.md progressive confirmation findings
- **Implementation Files:**
  - server/app.py
  - web/src/hooks/useConfirmationFlow.ts
  - web/src/components/IntentConfirmation.tsx
  - web/src/components/SideEffectAnalysis.tsx
  - web/src/App.tsx
  - api/openapi.yaml
  - tests/e2e/test_login_flow.py

### Analysis Methodology
- Static code review of backend and frontend confirmation logic
- Comparison against design.md requirements
- Review of existing tests and gap documentation

## Design Requirements vs Implementation

### Requirement: Three-stage progressive confirmation
- **Design Specification:** Intent → Change → Side-Effect stages with ability to cancel or return at each stage.
- **Implementation Status:** ⚠️ Partial
- **Implementation Location:** Backend endpoints `/confirm-intent`, `/confirm-changes`, `/confirm-side-effects`; frontend `useConfirmationFlow` hook and UI components.
- **Implementation Details:** Backend records per-stage confirmations, but OpenAPI spec and tests still target a single `/confirm` endpoint.
- **Compliance Assessment:** Stage transitions implemented, but API contract inconsistent with design.

### Requirement: Stage rollback and cancellation
- **Design Specification:** Each stage can be cancelled or returned; failures must not mutate canonical state.
- **Implementation Status:** ⚠️ Partial
- **Implementation Location:** `useConfirmationFlow.goBack` and `cancel` enable UI navigation; backend lacks explicit cancellation endpoints.
- **Compliance Assessment:** Frontend can return to earlier stages; backend does not offer rollback/cancel operations.

### Requirement: Unified confirmation API
- **Design Specification:** Design and OpenAPI expect a single `/confirm` endpoint with `stage` parameter.
- **Implementation Status:** ❌ Missing/Out-of-sync
- **Implementation Location:** OpenAPI defines `/sessions/{sid}/confirm`; backend exposes separate endpoints.
- **Compliance Assessment:** Divergent API contracts cause integration issues and failing tests.

## Frontend vs Backend Integration
- Frontend `App.tsx` renders progressive confirmation stages but relies on local state and placeholder handlers.
- Server endpoints require authentication and record confirmations, yet the frontend is not wired to these APIs.
- E2E test `test_login_flow.py` still calls the deprecated `/confirm` endpoint, indicating integration lag.

## State Machine Compliance
- Backend enforces stage order: change confirmation requires prior intent confirmation; side-effect confirmation requires changes confirmation.
- Frontend state machine in `useConfirmationFlow` mirrors the three-stage flow with ability to proceed and go back.
- Lack of cancellation/rollback paths and inconsistent API endpoints reduce overall compliance.

## Critical Missing Features
1. **OpenAPI & Test Alignment:** OpenAPI spec and tests not updated to new endpoints.
2. **Cancellation/Rollback:** Backend lacks endpoints for cancelling a proposal or rolling back stages.
3. **Commit Integration:** Frontend commit handler disabled; progressive confirmation not tied into commit workflow.
4. **Side-effect Auto-fix Feedback:** Backend supports auto-fixes, but frontend only toggles local state without confirming to server.

## Testing Coverage
- Only `tests/e2e/test_login_flow.py` exercises progressive confirmation and targets obsolete endpoints.
- No unit tests for individual confirmation stages or rollback scenarios.

## Recommendations
1. Update OpenAPI spec, frontend API client, and tests to use `/confirm-intent`, `/confirm-changes`, and `/confirm-side-effects` endpoints—or consolidate back to a single endpoint consistently across stack.
2. Implement cancellation/rollback endpoints and wire them into frontend `cancel` and `goBack` actions.
3. Integrate confirmation calls in frontend `App.tsx`, enabling commit once side effects are confirmed.
4. Expand test suite with stage-specific and cancellation scenarios.

**Analysis Complete:** ✅ Yes
