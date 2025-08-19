# FastAPI Testing Best Practices Guide

## 🎯 Testing Strategy Overview

This project implements a **3-tier testing strategy** for FastAPI applications:

### 1. **Unit Tests** - Fast & Isolated
- ✅ Use `TestClient` (no real server)
- ✅ Mock external dependencies
- ✅ Fast execution (< 1s per test)
- ✅ Run on every commit

### 2. **Integration Tests** - Database + App
- ✅ Use `TestClient` with real database
- ✅ Test component interactions
- ✅ Medium execution time

### 3. **E2E Tests** - Full System
- ✅ Start real server automatically
- ✅ Self-contained (no manual setup)
- ✅ Test complete user workflows
- ✅ Slower execution (run on PR/deploy)

## 📁 Project Structure

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/                    # Unit tests (fast, no server)
│   ├── test_sessions_unit.py
│   └── test_auth_unit.py
├── integration/             # Integration tests (DB + app)
│   └── test_api_integration.py
├── e2e/                     # End-to-end tests
│   ├── conftest.py          # E2E-specific fixtures
│   └── test_user_flows_e2e.py
└── pytest.ini              # Pytest configuration
```

## 🚀 Quick Start

### Run Tests
```bash
# Unit tests only (fast)
make test-unit

# E2E tests with self-contained server
make test-e2e

# All tests
make test-all

# With coverage
make test-coverage

# Watch mode (re-run on changes)
make test-watch
```

### Run Specific Tests
```bash
# Single test file
uv run pytest tests/unit/test_sessions_unit.py -v

# Single test function
uv run pytest tests/unit/test_sessions_unit.py::test_create_session -v

# By marker
uv run pytest -m unit -v
uv run pytest -m e2e -v
```

## ✅ Unit Test Best Practices

### ✅ DO: Use TestClient
```python
from fastapi.testclient import TestClient
from server.app import app

def test_create_session(authenticated_client):
    response = authenticated_client.post("/sessions")
    assert response.status_code == 200
```

### ❌ DON'T: Start real server for unit tests
```python
# DON'T DO THIS in unit tests
import subprocess
process = subprocess.Popen(["uvicorn", "app:app"])  # Too slow!
```

### ✅ DO: Mock external dependencies
```python
@pytest.fixture
def mock_llm_analyzer(monkeypatch):
    mock = Mock()
    mock.analyze.return_value = {"intentions": []}
    monkeypatch.setattr("server.analyzer.analyzer", mock)
    return mock
```

## 🌐 E2E Test Best Practices

### ✅ DO: Self-contained server setup
```python
@contextmanager
def test_server():
    port = find_free_port()
    process = subprocess.Popen([
        "uvicorn", "server.app:app",
        "--port", str(port)
    ])
    # Wait for server to start
    yield f"http://127.0.0.1:{port}"
    # Clean shutdown
    process.terminate()
```

### ✅ DO: Use module-scoped fixtures
```python
@pytest.fixture(scope="module")
def server_url():
    """Start server once per test module"""
    with test_server() as url:
        yield url
```

### ✅ DO: Test real HTTP requests
```python
def test_complete_flow_e2e(server_url, e2e_headers):
    # Real HTTP requests to real server
    response = requests.post(f"{server_url}/sessions", headers=e2e_headers)
    assert response.status_code == 200
```

## 🔧 Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
markers =
    unit: Unit tests (fast, no server)
    e2e: End-to-end tests (with real server)
    slow: Slow running tests

addopts = -v --strict-markers
```

### Makefile Commands
```makefile
test-unit:     ## Fast unit tests only
test-e2e:      ## E2E tests with server
test-fast:     ## Unit tests excluding slow ones
test-all:      ## All tests
test-coverage: ## Tests with coverage report
```

## 🎯 When to Use Each Type

### Unit Tests (`TestClient`)
- ✅ API endpoint logic
- ✅ Request/response validation
- ✅ Authentication/authorization
- ✅ Business logic validation
- ✅ Fast feedback during development

### E2E Tests (Real Server)
- ✅ Complete user workflows
- ✅ Multi-step processes
- ✅ Integration with external services
- ✅ Performance testing
- ✅ Production-like validation

## 🚨 Common Pitfalls to Avoid

### ❌ Starting server for unit tests
```python
# DON'T: Too slow for unit tests
def test_endpoint():
    subprocess.run(["uvicorn", "app:app"])  # BAD!
    response = requests.get("http://localhost:8000/health")
```

### ❌ Manual server setup for E2E
```python
# DON'T: Requires manual setup
def test_e2e():
    # Assumes server is already running - BAD!
    response = requests.get("http://localhost:8000/health")
```

### ❌ Port conflicts
```python
# DON'T: Hard-coded ports cause conflicts
subprocess.Popen(["uvicorn", "app:app", "--port", "8000"])  # BAD!

# DO: Use dynamic port allocation
port = find_free_port()
subprocess.Popen(["uvicorn", "app:app", "--port", str(port)])  # GOOD!
```

### ❌ Forgetting cleanup
```python
# DON'T: Leave processes running
def test_e2e():
    process = subprocess.Popen(["uvicorn", "app:app"])
    # Missing: process.terminate()  # BAD!

# DO: Use context managers for cleanup
@contextmanager
def test_server():
    process = subprocess.Popen(["uvicorn", "app:app"])
    try:
        yield "http://localhost:8000"
    finally:
        process.terminate()  # GOOD!
```

## 📊 Performance Comparison

| Test Type | Execution Time | Server Startup | Use Case |
|-----------|---------------|----------------|----------|
| Unit | ~0.1s per test | No server | Fast feedback |
| Integration | ~0.5s per test | TestClient | Component testing |
| E2E | ~2s per test | Real server | Full workflows |

## 🎉 Benefits of This Approach

### Unit Tests with TestClient
- ⚡ **Fast**: No network overhead
- 🔒 **Isolated**: No external dependencies
- 🧪 **Deterministic**: Predictable results
- 🔄 **Parallelizable**: Run tests concurrently

### E2E Tests with Self-Contained Server
- 🚀 **Self-contained**: No manual setup required
- 🔧 **Automated**: Start/stop server automatically
- 🎯 **Realistic**: Tests production-like scenarios
- 🛡️ **Robust**: Handles port conflicts gracefully

## 📚 Additional Resources

- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/best-practices.html)
- [TestClient Documentation](https://www.starlette.io/testclient/)

---

**Summary**: Use `TestClient` for unit tests (fast feedback), real servers for E2E tests (realistic validation), and make everything self-contained for maintainability.
