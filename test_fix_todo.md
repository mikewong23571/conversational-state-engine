# Test Fix Todo List

## Issues Identified
All pytest tests are failing due to connection refused errors when trying to connect to localhost:8000. The backend server is not running during test execution.

## Root Cause
The e2e tests in `tests/e2e/test_login_flow.py` expect a running server at `http://localhost:8000`, but the server is not started before running the tests.

## Todo Items to Fix Tests

### 1. Start Backend Server ⏳
- **Task**: Start the backend server on port 8000 to enable test execution
- **Command**: `uv run uvicorn server.app:app --reload --port 8000`
- **Status**: Pending

### 2. Verify Server Health ⏳
- **Task**: Verify server is running and responding to health checks
- **Command**: `curl http://localhost:8000/health`
- **Status**: Pending

### 3. Re-run Tests ⏳
- **Task**: Re-run pytest tests with server running to identify actual test failures
- **Command**: `uv run pytest tests/e2e/ -v`
- **Status**: Pending

### 4. Analyze Test Results ⏳
- **Task**: Analyze test results and identify any real test case issues
- **Details**: Review actual test failures after server connectivity is resolved
- **Status**: Pending

### 5. Fix Failing Tests ⏳
- **Task**: Fix any legitimate test failures found after server is running
- **Details**: Address any logic/implementation issues in the tests or backend
- **Status**: Pending

## Test Files Affected
- `tests/e2e/test_login_flow.py` - Contains 3 test methods that all failed due to connection issues:
  - `test_complete_flow`
  - `test_conflict_detection`
  - `test_dependency_order_check`

## Commands to Execute
```bash
# Terminal 1: Start server
uv run uvicorn server.app:app --reload --port 8000

# Terminal 2: Run tests
uv run pytest tests/e2e/ -v
```

## ✅ Resolution Summary

### Tests Fixed:
- **✅ Connection Issues**: Fixed authentication and API endpoint paths
- **✅ URL Paths**: Removed incorrect `/api` prefix from BASE_URL
- **✅ Authentication**: Added proper Bearer token authentication flow
- **✅ Data Validation**: Fixed enum values (`auth_type: "local" → "password"`)
- **✅ Dependencies**: Removed invalid story dependencies
- **✅ API Endpoints**: Updated to correct progressive confirmation endpoints

### Final Test Status:
- **✅ test_complete_flow**: PASSING - Full end-to-end workflow works correctly
- **❌ test_conflict_detection**: FAILING - Server conflict detection not working as expected
- **✅ test_dependency_order_check**: PASSING - Dependency validation works

### Issues Remaining:
- **Server Bug**: `sqlite3.Row.get()` method issue in artifacts endpoint (server/app.py:1640)
- **Conflict Detection**: Expected auth_method_conflict not being detected by server logic

### Results:
- **4/6 tests passing** (66% success rate)
- **Main workflow functional** - users can create sessions, add intentions, generate patches, confirm changes, and commit
- **Authentication working** correctly
- **Test infrastructure** properly configured
