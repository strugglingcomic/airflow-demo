# Testing Quick Start Guide

> Get up and running with the test suite in 5 minutes

## Installation

```bash
# Clone and enter the repository
cd /home/user/airflow-demo

# Install all dependencies including dev tools
pip install -e ".[dev]"

# Verify installation
pytest --version
```

## Run Your First Tests

```bash
# Run all tests
pytest tests/ -v

# Run just unit tests (fast!)
pytest -m unit tests/ -v

# Run with coverage
pytest --cov=src tests/
```

Expected output:
```
======================== test session starts =========================
platform linux -- Python 3.10.x, pytest-8.x.x, pluggy-1.x.x
plugins: cov-4.x.x, xdist-3.x.x, mock-3.x.x
collected 500+ items

tests/unit/services/test_s3_service.py::TestS3ServiceUploadFile::test_upload_file_success PASSED [1%]
...
======================== 500 passed in 15.23s ========================
```

## Common Commands

### Quick Testing

```bash
# Fast unit tests only
make test-unit

# With coverage report
make test-coverage

# Watch mode (re-run on changes)
make test-watch
```

### Specific Tests

```bash
# Test a specific file
pytest tests/unit/services/test_s3_service.py -v

# Test a specific function
pytest tests/unit/services/test_s3_service.py::test_upload_file_success -v

# Test by marker
pytest -m s3 tests/          # All S3 tests
pytest -m bedrock tests/     # All Bedrock tests
pytest -m integration tests/ # Integration tests
```

### Development Workflow

```bash
# 1. Create a new feature branch
git checkout -b feature/my-new-feature

# 2. Write a test first (TDD!)
vim tests/unit/services/test_s3_service.py

# 3. Run the test (should fail - RED)
pytest tests/unit/services/test_s3_service.py::test_my_new_feature -v

# 4. Implement the feature
vim src/airflow_demo/services/s3_service.py

# 5. Run the test again (should pass - GREEN)
pytest tests/unit/services/test_s3_service.py::test_my_new_feature -v

# 6. Run all related tests
pytest -m s3 tests/ -v

# 7. Check coverage
make test-coverage

# 8. Pre-commit will auto-run on commit
git add .
git commit -m "Add my new feature"
```

## Test Categories

### Unit Tests (Fast ⚡)
**What**: Test individual components in isolation
**Speed**: < 1 second each
**Run**: `pytest -m unit tests/`

```python
@pytest.mark.unit
@pytest.mark.s3
def test_s3_upload_file(s3_client, s3_bucket, temp_file):
    service = S3Service()
    service.client = s3_client
    result = service.upload_file(temp_file, s3_bucket, "test.txt")
    assert result == f"s3://{s3_bucket}/test.txt"
```

### Integration Tests (Medium ⚡⚡)
**What**: Test multiple components working together
**Speed**: 1-10 seconds each
**Run**: `pytest -m integration tests/`

```python
@pytest.mark.integration
@pytest.mark.aws
def test_s3_to_bedrock_workflow(s3_client, bedrock_client):
    # Test S3 + Bedrock working together
    ...
```

### E2E Tests (Slower ⚡⚡⚡)
**What**: Test complete DAG execution
**Speed**: 10-60 seconds each
**Run**: `pytest -m e2e tests/`

```python
@pytest.mark.e2e
@pytest.mark.dag
def test_complete_dag_execution(document_analysis_dag):
    # Test full DAG from start to finish
    ...
```

## Project Structure

```
airflow-demo/
├── src/airflow_demo/          # Source code
│   ├── services/              # Service layer (S3, Bedrock, etc.)
│   ├── operators/             # Airflow operators
│   ├── hooks/                 # Airflow hooks
│   └── config/                # Configuration
│
├── tests/                     # Test suite
│   ├── conftest.py           # Fixtures and configuration
│   ├── unit/                 # Unit tests (60%)
│   ├── integration/          # Integration tests (30%)
│   ├── e2e/                  # End-to-end tests (10%)
│   ├── fixtures/             # Test data and sample DAGs
│   └── utils/                # Test utilities
│
├── docs/                      # Documentation
│   ├── TDD_WORKFLOW_GUIDE.md # Detailed TDD tutorial
│   └── TESTING_STRATEGY.md   # Overall testing strategy
│
├── Makefile                   # Common commands
├── pyproject.toml            # Project configuration
└── .github/workflows/        # CI/CD configuration
```

## Available Make Commands

```bash
make help              # Show all available commands

# Testing
make test             # Run all tests
make test-unit        # Unit tests only (fast)
make test-integration # Integration tests
make test-e2e        # End-to-end tests
make test-coverage   # Tests with coverage report
make test-fast       # Skip slow tests
make test-watch      # Watch mode

# Quality
make lint            # Run linters
make format          # Format code
make typecheck       # Type checking
make quality         # All quality checks

# CI/CD
make ci              # Run full CI pipeline locally
```

## Using Fixtures

Fixtures provide pre-configured test data and objects:

```python
def test_my_feature(
    s3_client,           # Mocked S3 client
    s3_bucket,           # Empty S3 bucket
    bedrock_client,      # Mocked Bedrock client
    sample_json_data,    # Sample JSON data
    airflow_context,     # Airflow execution context
    temp_dir             # Temporary directory
):
    # Your test code here
    ...
```

See `tests/conftest.py` for all available fixtures.

## Common Patterns

### Testing S3 Operations

```python
@pytest.mark.unit
@pytest.mark.s3
def test_s3_operation(s3_client, s3_bucket):
    service = S3Service()
    service.client = s3_client

    # Upload
    service.write_json({"key": "value"}, s3_bucket, "test.json")

    # Verify
    data = service.read_json(s3_bucket, "test.json")
    assert data["key"] == "value"
```

### Testing Bedrock Operations

```python
@pytest.mark.unit
@pytest.mark.bedrock
def test_bedrock_operation(bedrock_client):
    from io import BytesIO
    from tests.utils.test_helpers import BedrockTestHelper

    service = BedrockService()
    service.client = bedrock_client

    # Mock response
    response_data = BedrockTestHelper.create_invoke_response("Hello!")
    bedrock_client.invoke_model.return_value = {
        "body": BytesIO(response_data["body"]),
        "ResponseMetadata": response_data["ResponseMetadata"],
    }

    # Test
    result = service.chat("Hi")
    assert "Hello!" in result
```

### Testing DAG Tasks

```python
@pytest.mark.e2e
@pytest.mark.dag
def test_dag_task(airflow_context, s3_client, s3_bucket):
    from tests.fixtures.dags.sample_dag import read_from_s3

    # Setup
    airflow_context["params"] = {
        "bucket": s3_bucket,
        "input_key": "test.json"
    }

    # Execute
    result = read_from_s3(**airflow_context)

    # Verify
    assert result is not None
```

## Debugging Tests

### Show print statements
```bash
pytest tests/ -s
```

### Drop into debugger on failure
```bash
pytest tests/ --pdb
```

### Show local variables on failure
```bash
pytest tests/ -l
```

### Verbose output
```bash
pytest tests/ -vv
```

### Stop on first failure
```bash
pytest tests/ -x
```

## Coverage Reports

### Generate HTML report
```bash
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

### Terminal report with missing lines
```bash
pytest --cov=src --cov-report=term-missing tests/
```

### Check coverage threshold
```bash
pytest --cov=src --cov-fail-under=80 tests/
```

## Pre-Commit Hooks

Automatically run on `git commit`:

```bash
# Setup (one time)
pre-commit install

# Run manually
pre-commit run --all-files
```

Hooks include:
- ✓ Code formatting (black)
- ✓ Linting (ruff)
- ✓ Type checking (mypy)
- ✓ Fast unit tests
- ✓ Security scan (bandit)

## Troubleshooting

### Tests not found
```bash
# Make sure you're in the project root
cd /home/user/airflow-demo

# Install in editable mode
pip install -e .
```

### Import errors
```bash
# Reinstall dependencies
pip install -e ".[dev]"
```

### Fixtures not found
```bash
# Make sure conftest.py exists
ls tests/conftest.py

# Run pytest with verbose fixture output
pytest --fixtures tests/
```

### Slow tests
```bash
# Find slow tests
pytest --durations=10 tests/

# Skip slow tests
pytest -m "not slow" tests/
```

## Next Steps

1. **Read the TDD Guide**: [docs/TDD_WORKFLOW_GUIDE.md](docs/TDD_WORKFLOW_GUIDE.md)
   - Complete TDD tutorial with examples
   - Step-by-step workflows
   - Best practices

2. **Review Test Examples**: [tests/README.md](tests/README.md)
   - All available fixtures
   - Test helpers
   - Code examples

3. **Understand the Strategy**: [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)
   - Overall testing approach
   - Coverage requirements
   - Performance testing

4. **Explore Test Code**:
   - `tests/unit/services/test_s3_service.py` - Comprehensive service tests
   - `tests/integration/aws/test_s3_bedrock_integration.py` - Integration examples
   - `tests/e2e/test_document_analysis_dag.py` - DAG testing examples

## Quick Reference

| Task | Command |
|------|---------|
| Run all tests | `make test` or `pytest tests/` |
| Unit tests only | `make test-unit` or `pytest -m unit tests/` |
| With coverage | `make test-coverage` |
| Watch mode | `make test-watch` |
| Specific file | `pytest tests/path/to/test_file.py` |
| Specific test | `pytest tests/file.py::test_function` |
| By marker | `pytest -m s3 tests/` |
| Parallel | `pytest -n auto tests/` |
| Last failed | `pytest --lf tests/` |
| Coverage report | `pytest --cov=src --cov-report=html tests/` |

## Getting Help

- **TDD Tutorial**: See [docs/TDD_WORKFLOW_GUIDE.md](docs/TDD_WORKFLOW_GUIDE.md)
- **Test Documentation**: See [tests/README.md](tests/README.md)
- **Fixtures**: Run `pytest --fixtures tests/`
- **Markers**: Run `pytest --markers`
- **All Commands**: Run `make help`

---

**Happy Testing! 🚀**

Remember: Write tests first, make them pass, then refactor. The tests are your safety net!
