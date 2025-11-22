.PHONY: help install test test-unit test-integration test-e2e test-fast test-coverage test-watch lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package and dependencies
	pip install -e ".[dev]"

# ============================================================================
# Testing Targets
# ============================================================================

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only (fast)
	pytest -m unit tests/ -v

test-integration: ## Run integration tests
	pytest -m integration tests/ -v

test-e2e: ## Run end-to-end tests
	pytest -m e2e tests/ -v

test-fast: ## Run tests excluding slow ones
	pytest -m "not slow" tests/ -v

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term-missing tests/
	@echo "Coverage report generated in htmlcov/index.html"

test-coverage-xml: ## Generate XML coverage report for CI
	pytest --cov=src --cov-report=xml --cov-report=term tests/

test-watch: ## Run tests in watch mode
	pytest-watch tests/ -- -v

test-parallel: ## Run tests in parallel
	pytest -n auto tests/ -v

# Specific AWS service tests
test-s3: ## Run S3 tests only
	pytest -m s3 tests/ -v

test-bedrock: ## Run Bedrock tests only
	pytest -m bedrock tests/ -v

test-secrets: ## Run Secrets Manager tests only
	pytest -m secrets tests/ -v

test-dag: ## Run DAG tests only
	pytest -m dag tests/ -v

# ============================================================================
# Code Quality Targets
# ============================================================================

lint: ## Run linters (ruff)
	ruff check src/ tests/

lint-fix: ## Fix linting issues automatically
	ruff check --fix src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting
	black --check src/ tests/

typecheck: ## Run type checking with mypy
	mypy src/

quality: lint format-check typecheck ## Run all quality checks

# ============================================================================
# Cleaning Targets
# ============================================================================

clean: ## Clean up temporary files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +

clean-all: clean ## Deep clean including build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

# ============================================================================
# Development Targets
# ============================================================================

dev-setup: install ## Set up development environment
	pre-commit install

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# ============================================================================
# Documentation Targets
# ============================================================================

docs-tdd: ## Open TDD workflow guide
	@cat docs/TDD_WORKFLOW_GUIDE.md

# ============================================================================
# Airflow Targets
# ============================================================================

airflow-init: ## Initialize Airflow database
	airflow db init

airflow-webserver: ## Start Airflow webserver
	airflow webserver --port 8080

airflow-scheduler: ## Start Airflow scheduler
	airflow scheduler

# ============================================================================
# CI/CD Targets
# ============================================================================

ci-test: ## Run tests as in CI
	pytest tests/ -v --junitxml=junit.xml --cov=src --cov-report=xml --cov-report=term

ci-quality: quality ## Run quality checks as in CI

ci: ci-quality ci-test ## Run full CI pipeline locally

# ============================================================================
# Utility Targets
# ============================================================================

list-tests: ## List all available tests
	pytest --collect-only tests/

show-markers: ## Show all pytest markers
	pytest --markers

show-fixtures: ## Show all available fixtures
	pytest --fixtures

stats: ## Show test statistics
	@echo "Test Statistics:"
	@echo "================"
	@echo "Total test files: $$(find tests -name 'test_*.py' | wc -l)"
	@echo "Total tests: $$(pytest --collect-only -q tests/ | grep -c 'test')"
	@echo ""
	@echo "By category:"
	@echo "  Unit tests: $$(pytest --collect-only -q -m unit tests/ 2>/dev/null | grep -c 'test' || echo 0)"
	@echo "  Integration tests: $$(pytest --collect-only -q -m integration tests/ 2>/dev/null | grep -c 'test' || echo 0)"
	@echo "  E2E tests: $$(pytest --collect-only -q -m e2e tests/ 2>/dev/null | grep -c 'test' || echo 0)"
