# Makefile for Conversational State Engine Testing

.PHONY: help test test-unit test-e2e test-all test-fast test-coverage clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Test commands
test-unit: ## Run fast unit tests only (no server)
	uv run pytest tests/unit/ -m unit -v

test-e2e: ## Run end-to-end tests (with server)
	uv run pytest tests/e2e/ -m e2e -v

test-fast: ## Run only fast unit tests
	uv run pytest tests/unit/ -m "unit and not slow" -v

test-all: ## Run all tests (unit + e2e)
	uv run pytest tests/ -v

test: test-unit ## Default: run unit tests

test-coverage: ## Run tests with coverage report
	uv run pytest tests/unit/ --cov=server --cov-report=html --cov-report=term-missing

# Development commands
test-watch: ## Run tests in watch mode (re-run on file changes)
	uv run pytest-watch -- tests/unit/ -m unit

test-debug: ## Run tests with debugging enabled
	uv run pytest tests/unit/ -m unit -v -s --tb=long

# Validation commands
test-original: ## Run the original e2e test (for comparison)
	uv run pytest tests/e2e/test_login_flow.py -v

validate-server: ## Check if server is running and healthy
	@curl -s http://localhost:8000/health || echo "Server not running on port 8000"

# Cleanup
clean: ## Clean up test artifacts
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Examples
example-unit: ## Example: run a specific unit test
	uv run pytest tests/unit/test_sessions_unit.py::test_create_session -v

example-e2e: ## Example: run a specific e2e test
	uv run pytest tests/e2e/test_user_flows_e2e.py::test_complete_user_flow_e2e -v
