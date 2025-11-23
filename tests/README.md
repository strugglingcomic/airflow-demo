# Test Suite Documentation

This directory contains the comprehensive test suite for the Airflow + AWS integration project.

## Directory Structure

```
tests/
├── conftest.py              # Root pytest configuration and shared fixtures
├── __init__.py
│
├── unit/                    # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── conftest.py         # Unit test specific fixtures
│   ├── services/           # Service layer tests
│   │   ├── test_s3_service.py
│   │   ├── test_bedrock_service.py
│   │   └── test_secrets_service.py
│   ├── operators/          # Operator tests
│   │   ├── test_bedrock_operator.py
│   │   └── test_s3_operators.py
│   ├── hooks/              # Hook tests
│   │   └── test_bedrock_hook.py
│   └── config/             # Configuration tests
│       └── test_config.py
│
├── integration/             # Integration tests (moderate speed)
│   ├── __init__.py
│   ├── aws/                # AWS service integration
│   │   ├── test_s3_bedrock_integration.py
│   │   ├── test_s3_secrets_integration.py
│   │   └── test_full_aws_integration.py
│   └── dags/               # DAG component integration
│       └── test_dag_tasks_integration.py
│
├── e2e/                     # End-to-end tests (slower)
│   ├── __init__.py
│   └── test_document_analysis_dag.py
│
├── fixtures/                # Test fixtures and sample data
│   ├── __init__.py
│   ├── dags/               # Sample DAG files
│   │   └── sample_dag.py
│   ├── data/               # Sample data files
│   │   ├── sample.json
│   │   └── sample.csv
│   └── responses/          # Mock AWS responses
│       └── bedrock_responses.json
│
└── utils/                   # Test utilities
    ├── __init__.py
    └── test_helpers.py     # Helper functions and classes
```

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in complete isolation

**Characteristics**:
- Extremely fast (< 1 second per test)
- No external dependencies
- Extensive use of mocks and fixtures
- Focus on single function/method behavior
- High code coverage

**When to use**:
- Testing service methods
- Testing operator logic
- Testing utility functions
- Testing error handling
- Testing edge cases

**Example**:
```python
@pytest.mark.unit
@pytest.mark.s3
def test_s3_upload_file(s3_client, s3_bucket, temp_file):
    service = S3Service()
    service.client = s3_client

    result = service.upload_file(temp_file, s3_bucket, "test.txt")

    assert result == f"s3://{s3_bucket}/test.txt"
    assert service.object_exists(s3_bucket, "test.txt")
```

### Integration Tests (`tests/integration/`)

**Purpose**: Test multiple components working together

**Characteristics**:
- Moderate speed (1-10 seconds per test)
- Test service-to-service interactions
- Use mocked AWS services (moto)
- Test data flow between components
- Test error propagation

**When to use**:
- Testing workflows spanning multiple services
- Testing data transformation pipelines
- Testing error handling across services
- Testing batch operations

**Example**:
```python
@pytest.mark.integration
@pytest.mark.aws
def test_s3_to_bedrock_workflow(s3_client, bedrock_client, s3_bucket):
    s3_service = S3Service()
    bedrock_service = BedrockService()

    # Upload document
    s3_service.write_json({"text": "Document"}, s3_bucket, "doc.json")

    # Read and analyze
    doc = s3_service.read_json(s3_bucket, "doc.json")
    analysis = bedrock_service.analyze_document(doc["text"], "Summarize")

    # Write results
    s3_service.write_json({"analysis": analysis}, s3_bucket, "result.json")

    # Verify
    assert s3_service.object_exists(s3_bucket, "result.json")
```

### End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete DAG execution from start to finish

**Characteristics**:
- Slower (10-60 seconds per test)
- Test entire DAG workflows
- Test task dependencies
- Test XCom data passing
- Test DAG-level error handling

**When to use**:
- Testing complete DAG runs
- Testing task orchestration
- Testing failure recovery
- Testing DAG configuration
- Validating business workflows

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.dag
def test_complete_dag_execution(document_analysis_dag, execution_date):
    # Setup test data
    # Execute DAG tasks in sequence
    # Verify final results
    # Check all tasks succeeded
```

## Available Fixtures

### AWS Service Fixtures

Defined in `tests/conftest.py`:

- `aws_credentials` - Mock AWS credentials
- `mock_aws_services` - Mock all AWS services
- `s3_client` - Mocked S3 client
- `s3_resource` - Mocked S3 resource
- `s3_bucket` - Empty test S3 bucket
- `s3_bucket_with_data` - S3 bucket with sample data
- `s3_versioned_bucket` - S3 bucket with versioning
- `secrets_client` - Mocked Secrets Manager client
- `sample_secrets` - Pre-populated secrets
- `bedrock_client` - Mocked Bedrock client
- `bedrock_model_id` - Default Bedrock model ID
- `bedrock_streaming_response` - Mock streaming response
- `bedrock_non_streaming_response` - Mock non-streaming response

### Airflow Fixtures

- `sample_dag` - Basic test DAG
- `execution_date` - Fixed execution date
- `dag_run` - Test DAG run
- `task_instance` - Test task instance
- `airflow_context` - Complete execution context
- `dag_bag` - DAG bag for loading DAGs

### Test Data Fixtures

- `sample_json_data` - Sample JSON document
- `sample_csv_data` - Sample CSV data
- `sample_bedrock_request` - Sample Bedrock request
- `large_json_dataset` - Large dataset for performance tests
- `faker_instance` - Faker for generating test data

### Utility Fixtures

- `temp_dir` - Temporary directory
- `temp_file` - Temporary test file
- `frozen_time` - Freeze time for deterministic tests
- `mock_logger` - Mock logger
- `env_vars` - Environment variable manager
- `performance_timer` - Performance measurement
- `metrics_collector` - Metrics collection

## Test Markers

Use markers to categorize and filter tests:

```bash
# Run by test level
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only
pytest -m e2e            # End-to-end tests only

# Run by AWS service
pytest -m s3             # S3 tests
pytest -m bedrock        # Bedrock tests
pytest -m secrets        # Secrets Manager tests
pytest -m aws            # All AWS tests

# Run by speed
pytest -m "not slow"     # Skip slow tests
pytest -m slow           # Slow tests only

# Run by component
pytest -m dag            # DAG tests
pytest -m requires_airflow  # Tests requiring Airflow scheduler
```

### Available Markers

Defined in `pyproject.toml`:

- `unit` - Unit tests (fast, isolated)
- `integration` - Integration tests (slower, multiple components)
- `e2e` - End-to-end tests (slowest, full system)
- `aws` - Tests requiring AWS services
- `s3` - S3-specific tests
- `secrets` - Secrets Manager tests
- `bedrock` - Bedrock/AI tests
- `dag` - DAG execution tests
- `slow` - Slow running tests
- `requires_airflow` - Tests requiring Airflow scheduler

## Test Helpers

Located in `tests/utils/test_helpers.py`:

### S3TestHelper

```python
from tests.utils.test_helpers import S3TestHelper

# Create mock S3 objects
obj = S3TestHelper.create_s3_object(bucket, key, content)

# Create list response
response = S3TestHelper.create_s3_list_response(bucket, keys)
```

### BedrockTestHelper

```python
from tests.utils.test_helpers import BedrockTestHelper

# Create invoke response
response = BedrockTestHelper.create_invoke_response("Hello!")

# Create streaming chunks
chunks = BedrockTestHelper.create_streaming_chunks("Response text")

# Create request payload
payload = BedrockTestHelper.create_request_payload("Prompt")
```

### SecretsTestHelper

```python
from tests.utils.test_helpers import SecretsTestHelper

# Create secret response
response = SecretsTestHelper.create_secret_response(name, value)

# Create Airflow connection secret
secret = SecretsTestHelper.create_airflow_connection_secret(
    conn_type="aws",
    login="key",
    password="secret"
)
```

### DataBuilder

```python
from tests.utils.test_helpers import DataBuilder

builder = DataBuilder()

# Build test data
user = builder.build_user(name="John Doe")
transaction = builder.build_transaction(amount=100.00)
dataset = builder.build_dataset("build_user", count=100)
```

### AssertionHelper

```python
from tests.utils.test_helpers import AssertionHelper

# S3 assertions
AssertionHelper.assert_s3_object_exists(s3_client, bucket, key)
AssertionHelper.assert_s3_object_content(s3_client, bucket, key, "expected")

# Bedrock assertions
AssertionHelper.assert_bedrock_response_valid(response)

# Airflow assertions
AssertionHelper.assert_task_instance_success(task_instance)
AssertionHelper.assert_dag_run_success(dag_run)
```

## Running Tests

### Quick Start

```bash
# Install dependencies
make install

# Run all tests
make test

# Run unit tests (fast)
make test-unit

# Run with coverage
make test-coverage
```

### Detailed Commands

```bash
# All tests
pytest tests/ -v

# Specific category
pytest -m unit tests/
pytest -m integration tests/
pytest -m e2e tests/

# Specific file
pytest tests/unit/services/test_s3_service.py -v

# Specific test
pytest tests/unit/services/test_s3_service.py::test_upload_file_success -v

# With coverage
pytest --cov=src --cov-report=html tests/

# Parallel execution
pytest -n auto tests/

# Stop on first failure
pytest -x tests/

# Show print statements
pytest -s tests/

# Verbose output
pytest -vv tests/
```

### Watch Mode

```bash
# Re-run tests on file changes
pytest-watch tests/

# Or with make
make test-watch
```

## Writing New Tests

### 1. Choose the Right Test Level

```python
# Unit test - testing S3Service.upload_file in isolation
@pytest.mark.unit
@pytest.mark.s3
def test_s3_upload_file(s3_client, s3_bucket):
    service = S3Service()
    service.client = s3_client
    # Test single method

# Integration test - testing S3 + Bedrock together
@pytest.mark.integration
@pytest.mark.aws
def test_s3_bedrock_pipeline(s3_client, bedrock_client):
    # Test multiple services working together

# E2E test - testing complete DAG
@pytest.mark.e2e
@pytest.mark.dag
def test_complete_dag(dag):
    # Test full DAG execution
```

### 2. Use Appropriate Fixtures

```python
def test_my_feature(s3_client, s3_bucket, sample_json_data, temp_dir):
    # Use pre-configured fixtures instead of manual setup
    ...
```

### 3. Follow Naming Conventions

```python
# Test file names
test_s3_service.py          # ✓ Good
s3_tests.py                 # ✗ Bad

# Test function names
def test_upload_file_with_metadata_succeeds()  # ✓ Good - descriptive
def test_upload()                               # ✗ Bad - too vague

# Test class names
class TestS3ServiceUpload:  # ✓ Good
class S3Tests:              # ✗ Bad
```

### 4. Use Arrange-Act-Assert

```python
def test_s3_copy():
    # ARRANGE - Set up test conditions
    service = S3Service()
    service.client = s3_client
    s3_client.put_object(Bucket="src", Key="file", Body="data")

    # ACT - Execute the code being tested
    result = service.copy_object("src", "file", "dest", "file")

    # ASSERT - Verify the results
    assert result == "s3://dest/file"
    assert service.object_exists("dest", "file")
```

### 5. Add Appropriate Markers

```python
@pytest.mark.unit           # Required: test level
@pytest.mark.s3            # Optional: service/component
@pytest.mark.slow          # Optional: if test is slow
def test_my_feature():
    ...
```

## Coverage Requirements

Target coverage levels:

| Component | Target | Rationale |
|-----------|--------|-----------|
| Service Layer | 95-100% | Core business logic |
| Operators | 90-95% | Critical for DAG execution |
| Hooks | 85-90% | Airflow integration layer |
| DAG Files | 80-90% | Workflow orchestration |
| Utilities | 85-95% | Shared helper functions |
| **Overall** | **85%+** | Project health indicator |

### Checking Coverage

```bash
# Generate HTML report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing tests/

# Fail if coverage below 80%
pytest --cov=src --cov-fail-under=80 tests/
```

## Continuous Integration

Tests run automatically in CI/CD:

```bash
# Run CI suite locally
make ci

# Individual CI steps
make ci-quality    # Linting, formatting, type checking
make ci-test      # Full test suite with coverage
```

## Troubleshooting

### Tests Fail to Import Modules

```bash
# Install package in editable mode
pip install -e .
```

### Fixtures Not Found

Check that `conftest.py` files are in the correct locations and properly named.

### Mocked Services Not Working

Ensure you're patching at the point of use:

```python
# ✗ Bad
@patch("boto3.client")

# ✓ Good
@patch("src.airflow_demo.services.s3_service.boto3.client")
```

### Slow Test Execution

```bash
# Run in parallel
pytest -n auto tests/

# Skip slow tests
pytest -m "not slow" tests/

# Run only unit tests
pytest -m unit tests/
```

## Best Practices

1. **Write tests first** (TDD) - Define behavior before implementation
2. **Keep tests independent** - Each test should run in isolation
3. **Use descriptive names** - Test names should describe what they test
4. **One assertion per test** - Focus on testing one thing
5. **Use fixtures** - Avoid repetitive setup code
6. **Test error cases** - Don't just test happy paths
7. **Keep tests fast** - Unit tests should be < 1 second
8. **Mock external services** - Don't call real AWS services
9. **Clean up after tests** - Use fixtures for automatic cleanup
10. **Document complex tests** - Add docstrings explaining the test

## Resources

- [TDD Workflow Guide](../docs/TDD_WORKFLOW_GUIDE.md) - Comprehensive TDD tutorial
- [pytest Documentation](https://docs.pytest.org/) - pytest official docs
- [moto Documentation](https://docs.getmoto.org/) - AWS mocking library
- [Airflow Testing](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-dags) - Airflow testing guide

## Getting Help

If you have questions about testing:

1. Check the [TDD Workflow Guide](../docs/TDD_WORKFLOW_GUIDE.md)
2. Look at existing tests for examples
3. Review test utilities in `tests/utils/test_helpers.py`
4. Check fixture definitions in `tests/conftest.py`

Happy testing!
