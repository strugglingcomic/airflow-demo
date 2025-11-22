# TDD Workflow Guide for Airflow + AWS Integration

This guide demonstrates how to use Test-Driven Development (TDD) principles when building Airflow DAGs with AWS integration.

## Table of Contents

1. [TDD Philosophy](#tdd-philosophy)
2. [Setting Up Your Environment](#setting-up-your-environment)
3. [TDD Workflow Examples](#tdd-workflow-examples)
4. [Running Tests](#running-tests)
5. [Test Categories](#test-categories)
6. [Best Practices](#best-practices)

---

## TDD Philosophy

### The Red-Green-Refactor Cycle

```
1. RED:    Write a failing test first
2. GREEN:  Write minimal code to make it pass
3. REFACTOR: Improve the code while keeping tests green
```

### Why TDD?

- **Design First**: Tests force you to think about the API before implementation
- **Living Documentation**: Tests document how the code should be used
- **Confidence**: Comprehensive tests allow fearless refactoring
- **Fast Feedback**: Catch bugs early in the development cycle

---

## Setting Up Your Environment

### 1. Install Dependencies

```bash
# Install development dependencies
pip install -e ".[dev]"

# Verify pytest is installed
pytest --version
```

### 2. Configure Your IDE

#### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "-v"
  ],
  "python.testing.unittestEnabled": false
}
```

#### PyCharm

1. Go to Settings → Tools → Python Integrated Tools
2. Set Default test runner to "pytest"
3. Set pytest options: `-v --strict-markers`

---

## TDD Workflow Examples

### Example 1: Adding a New S3 Method

Let's add a method to copy multiple objects in S3 using TDD.

#### Step 1: Write the Test First (RED)

Create `tests/unit/services/test_s3_service.py`:

```python
@pytest.mark.unit
@pytest.mark.s3
def test_batch_copy_objects(s3_client, s3_bucket):
    """Test copying multiple objects at once."""
    service = S3Service()
    service.client = s3_client

    # Upload source files
    for i in range(3):
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=f"source/file_{i}.txt",
            Body=f"Content {i}"
        )

    # Copy all files
    copies = [
        ("source/file_0.txt", "dest/file_0.txt"),
        ("source/file_1.txt", "dest/file_1.txt"),
        ("source/file_2.txt", "dest/file_2.txt"),
    ]

    results = service.batch_copy_objects(s3_bucket, s3_bucket, copies)

    # Verify all copies succeeded
    assert len(results) == 3
    for dest_key in ["dest/file_0.txt", "dest/file_1.txt", "dest/file_2.txt"]:
        assert service.object_exists(s3_bucket, dest_key)
```

#### Step 2: Run the Test (Should FAIL)

```bash
pytest tests/unit/services/test_s3_service.py::test_batch_copy_objects -v
```

Expected output:
```
AttributeError: 'S3Service' object has no attribute 'batch_copy_objects'
```

#### Step 3: Implement the Minimal Code (GREEN)

Add to `src/airflow_demo/services/s3_service.py`:

```python
def batch_copy_objects(
    self,
    source_bucket: str,
    dest_bucket: str,
    copies: List[Tuple[str, str]]
) -> List[str]:
    """
    Copy multiple objects in batch.

    Args:
        source_bucket: Source bucket name
        dest_bucket: Destination bucket name
        copies: List of (source_key, dest_key) tuples

    Returns:
        List of destination S3 URIs
    """
    results = []
    for source_key, dest_key in copies:
        uri = self.copy_object(source_bucket, source_key, dest_bucket, dest_key)
        results.append(uri)
    return results
```

#### Step 4: Run the Test Again (Should PASS)

```bash
pytest tests/unit/services/test_s3_service.py::test_batch_copy_objects -v
```

Expected output:
```
✓ test_batch_copy_objects PASSED
```

#### Step 5: Refactor (Keep Tests GREEN)

Improve the implementation with error handling:

```python
def batch_copy_objects(
    self,
    source_bucket: str,
    dest_bucket: str,
    copies: List[Tuple[str, str]],
    raise_on_error: bool = True
) -> Dict[str, List[str]]:
    """
    Copy multiple objects in batch.

    Args:
        source_bucket: Source bucket name
        dest_bucket: Destination bucket name
        copies: List of (source_key, dest_key) tuples
        raise_on_error: Whether to raise on first error

    Returns:
        Dict with 'successful' and 'failed' lists
    """
    results = {"successful": [], "failed": []}

    for source_key, dest_key in copies:
        try:
            uri = self.copy_object(source_bucket, source_key, dest_bucket, dest_key)
            results["successful"].append(uri)
        except S3ServiceError as e:
            if raise_on_error:
                raise
            results["failed"].append({
                "source_key": source_key,
                "dest_key": dest_key,
                "error": str(e)
            })
            logger.warning(f"Failed to copy {source_key}: {e}")

    return results
```

Now add more tests for the improved version:

```python
def test_batch_copy_with_failures(s3_client, s3_bucket):
    """Test batch copy handles failures gracefully."""
    service = S3Service()
    service.client = s3_client

    # Upload one file
    s3_client.put_object(Bucket=s3_bucket, Key="exists.txt", Body="data")

    copies = [
        ("exists.txt", "dest/exists.txt"),
        ("missing.txt", "dest/missing.txt"),  # This will fail
    ]

    results = service.batch_copy_objects(
        s3_bucket, s3_bucket, copies, raise_on_error=False
    )

    assert len(results["successful"]) == 1
    assert len(results["failed"]) == 1
```

Run all tests to ensure refactoring didn't break anything:

```bash
pytest tests/unit/services/test_s3_service.py -v
```

---

### Example 2: Creating a New Bedrock Operator

Let's create a custom Airflow operator for Bedrock using TDD.

#### Step 1: Write the Test First

Create `tests/unit/operators/test_bedrock_operator.py`:

```python
import pytest
from airflow.utils.context import Context
from io import BytesIO

@pytest.mark.unit
@pytest.mark.bedrock
def test_bedrock_operator_basic_execution(bedrock_client, airflow_context):
    """Test BedrockOperator executes successfully."""
    from src.airflow_demo.operators.bedrock_operator import BedrockOperator
    from tests.utils.test_helpers import BedrockTestHelper

    # Mock response
    response_data = BedrockTestHelper.create_invoke_response("Hello from Claude!")
    bedrock_client.invoke_model.return_value = {
        "body": BytesIO(response_data["body"]),
        "ResponseMetadata": response_data["ResponseMetadata"],
    }

    # Create operator
    operator = BedrockOperator(
        task_id="test_bedrock",
        prompt="Say hello",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    )

    # Inject mocked client
    with patch("src.airflow_demo.operators.bedrock_operator.boto3.client") as mock:
        mock.return_value = bedrock_client

        # Execute
        result = operator.execute(context=airflow_context)

        # Verify
        assert "Hello from Claude!" in result
```

#### Step 2: Implement the Operator

Create `src/airflow_demo/operators/bedrock_operator.py`:

```python
from typing import Any, Dict, Optional
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from src.airflow_demo.services.bedrock_service import BedrockService


class BedrockOperator(BaseOperator):
    """
    Operator for invoking AWS Bedrock models.

    Args:
        prompt: The prompt to send to the model
        model_id: Bedrock model ID
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation
        system: Optional system prompt
    """

    template_fields = ("prompt", "system")
    ui_color = "#ff9900"

    @apply_defaults
    def __init__(
        self,
        *,
        prompt: str,
        model_id: str = BedrockService.CLAUDE_3_5_SONNET,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.prompt = prompt
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system = system

    def execute(self, context: Dict[str, Any]) -> str:
        """Execute the operator."""
        service = BedrockService(model_id=self.model_id)

        result = service.chat(
            prompt=self.prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system,
        )

        # Push to XCom
        context["ti"].xcom_push(key="bedrock_response", value=result)

        return result
```

#### Step 3: Add More Tests

```python
def test_bedrock_operator_with_template_fields(bedrock_client, airflow_context):
    """Test operator with Jinja templating."""
    from src.airflow_demo.operators.bedrock_operator import BedrockOperator

    # Add template variables to context
    airflow_context["ds"] = "2024-01-01"

    operator = BedrockOperator(
        task_id="templated_bedrock",
        prompt="Process data for {{ ds }}",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    )

    # Template rendering would happen here in real Airflow
    # For testing, verify template_fields is set correctly
    assert "prompt" in operator.template_fields
    assert "system" in operator.template_fields


def test_bedrock_operator_pushes_to_xcom(bedrock_client, airflow_context):
    """Test operator pushes result to XCom."""
    from src.airflow_demo.operators.bedrock_operator import BedrockOperator
    from tests.utils.test_helpers import BedrockTestHelper

    response_data = BedrockTestHelper.create_invoke_response("Test response")
    bedrock_client.invoke_model.return_value = {
        "body": BytesIO(response_data["body"]),
        "ResponseMetadata": response_data["ResponseMetadata"],
    }

    xcom_pushed = {}

    def mock_xcom_push(key, value):
        xcom_pushed[key] = value

    airflow_context["ti"].xcom_push = mock_xcom_push

    operator = BedrockOperator(
        task_id="xcom_test",
        prompt="Test",
    )

    with patch("src.airflow_demo.operators.bedrock_operator.boto3.client") as mock:
        mock.return_value = bedrock_client
        operator.execute(context=airflow_context)

    assert "bedrock_response" in xcom_pushed
    assert xcom_pushed["bedrock_response"] == "Test response"
```

---

### Example 3: Building a Complete DAG with TDD

#### Step 1: Write DAG Structure Tests

```python
@pytest.mark.e2e
@pytest.mark.dag
def test_new_dag_structure():
    """Test new DAG has correct structure."""
    from tests.fixtures.dags.my_new_dag import dag

    assert dag.dag_id == "my_new_workflow"
    assert len(dag.tasks) == 4

    # Test task dependencies
    extract_task = dag.get_task("extract_data")
    transform_task = dag.get_task("transform_data")

    assert transform_task in extract_task.downstream_list
```

#### Step 2: Write Task Tests

```python
@pytest.mark.unit
def test_extract_data_task(airflow_context, s3_client, s3_bucket):
    """Test data extraction task."""
    from tests.fixtures.dags.my_new_dag import extract_data

    # Setup
    s3_service = S3Service()
    s3_service.client = s3_client
    s3_service.write_json({"data": "test"}, s3_bucket, "source.json")

    airflow_context["params"] = {"bucket": s3_bucket}

    # Execute
    result = extract_data(**airflow_context)

    # Verify
    assert result is not None
    data = airflow_context["ti"].xcom_pull(key="extracted_data")
    assert data["data"] == "test"
```

#### Step 3: Implement the DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def extract_data(**context):
    from src.airflow_demo.services.s3_service import S3Service

    s3 = S3Service()
    bucket = context["params"]["bucket"]
    data = s3.read_json(bucket, "source.json")
    context["ti"].xcom_push(key="extracted_data", value=data)
    return data

with DAG(
    "my_new_workflow",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:

    extract = PythonOperator(
        task_id="extract_data",
        python_callable=extract_data,
    )
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit tests/

# Integration tests
pytest -m integration tests/

# End-to-end tests
pytest -m e2e tests/

# AWS-specific tests
pytest -m aws tests/

# S3 tests only
pytest -m s3 tests/

# Bedrock tests only
pytest -m bedrock tests/
```

### Run with Coverage

```bash
# Run with coverage report
pytest --cov=src --cov-report=html tests/

# Open coverage report
open htmlcov/index.html
```

### Run Tests in Parallel

```bash
# Run with 4 workers
pytest -n 4 tests/

# Auto-detect number of CPUs
pytest -n auto tests/
```

### Run Specific Test File

```bash
pytest tests/unit/services/test_s3_service.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/services/test_s3_service.py::test_upload_file_success -v
```

### Run Tests Matching Pattern

```bash
# Run all tests with "upload" in the name
pytest -k upload tests/

# Run all S3 and Bedrock tests
pytest -k "s3 or bedrock" tests/
```

### Skip Slow Tests

```bash
pytest -m "not slow" tests/
```

---

## Test Categories

### 1. Unit Tests

**Location**: `tests/unit/`

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast (< 1 second each)
- No external dependencies
- Use mocks extensively
- High code coverage

**Example**:
```python
@pytest.mark.unit
def test_s3_service_upload_file(s3_client, s3_bucket, temp_file):
    service = S3Service()
    service.client = s3_client

    result = service.upload_file(temp_file, s3_bucket, "test.txt")

    assert result == f"s3://{s3_bucket}/test.txt"
```

### 2. Integration Tests

**Location**: `tests/integration/`

**Purpose**: Test multiple components working together

**Characteristics**:
- Moderate speed (1-5 seconds each)
- Test service integration
- Use mocked AWS services
- Test data flow

**Example**:
```python
@pytest.mark.integration
@pytest.mark.aws
def test_s3_to_bedrock_workflow(s3_client, bedrock_client, s3_bucket):
    # Test complete workflow with multiple services
    s3_service = S3Service()
    bedrock_service = BedrockService()

    # Upload -> Process -> Download
    ...
```

### 3. End-to-End Tests

**Location**: `tests/e2e/`

**Purpose**: Test complete DAG execution

**Characteristics**:
- Slower (5-30 seconds each)
- Test full DAG runs
- Test task dependencies
- Test XCom data flow

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.dag
def test_complete_dag_execution(document_analysis_dag, execution_date):
    # Test full DAG from start to finish
    ...
```

---

## Best Practices

### 1. Test Naming Conventions

```python
# Good test names - descriptive and specific
def test_upload_file_with_metadata_succeeds()
def test_upload_to_nonexistent_bucket_raises_error()
def test_bedrock_streaming_returns_chunks()

# Bad test names - vague
def test_upload()
def test_error()
def test_bedrock()
```

### 2. Arrange-Act-Assert Pattern

```python
def test_s3_copy_object():
    # ARRANGE: Set up test data
    service = S3Service()
    service.client = s3_client
    s3_client.put_object(Bucket="bucket", Key="source", Body="data")

    # ACT: Execute the function being tested
    result = service.copy_object("bucket", "source", "bucket", "dest")

    # ASSERT: Verify the outcome
    assert result == "s3://bucket/dest"
    assert service.object_exists("bucket", "dest")
```

### 3. One Assertion Per Test (Usually)

```python
# Good - focused test
def test_upload_returns_s3_uri():
    result = service.upload_file(file, bucket, key)
    assert result == f"s3://{bucket}/{key}"

def test_upload_creates_object():
    service.upload_file(file, bucket, key)
    assert service.object_exists(bucket, key)

# Less ideal - testing multiple things
def test_upload():
    result = service.upload_file(file, bucket, key)
    assert result == f"s3://{bucket}/{key}"
    assert service.object_exists(bucket, key)
    assert result.startswith("s3://")
```

### 4. Use Fixtures for Common Setup

```python
# Bad - repetitive setup
def test_read_json():
    s3 = S3Service()
    s3.client = boto3.client("s3")
    s3.client.create_bucket(Bucket="test-bucket")
    ...

def test_write_json():
    s3 = S3Service()
    s3.client = boto3.client("s3")
    s3.client.create_bucket(Bucket="test-bucket")
    ...

# Good - use fixtures
@pytest.fixture
def s3_service_with_bucket(s3_client, s3_bucket):
    service = S3Service()
    service.client = s3_client
    return service, s3_bucket

def test_read_json(s3_service_with_bucket):
    service, bucket = s3_service_with_bucket
    ...
```

### 5. Test Error Cases

```python
def test_download_missing_file_raises_error():
    with pytest.raises(S3ObjectNotFoundError, match="Object not found"):
        service.download_file(bucket, "missing.txt", local_path)

def test_invalid_json_raises_error():
    s3_client.put_object(Bucket=bucket, Key="bad.json", Body=b"{invalid}")

    with pytest.raises(S3ServiceError, match="Invalid JSON"):
        service.read_json(bucket, "bad.json")
```

### 6. Use Parametrize for Similar Tests

```python
@pytest.mark.parametrize("model_id,expected_provider", [
    (BedrockService.CLAUDE_3_5_SONNET, "anthropic"),
    (BedrockService.CLAUDE_3_OPUS, "anthropic"),
    (BedrockService.CLAUDE_3_HAIKU, "anthropic"),
])
def test_model_ids_are_valid(model_id, expected_provider):
    assert expected_provider in model_id
```

### 7. Keep Tests Independent

```python
# Bad - tests depend on each other
def test_upload():
    service.upload_file(file, bucket, "test.txt")

def test_download():  # Depends on test_upload running first
    service.download_file(bucket, "test.txt", local_path)

# Good - each test is independent
def test_upload(s3_client, s3_bucket):
    service = S3Service()
    service.client = s3_client
    service.upload_file(file, s3_bucket, "test.txt")
    assert service.object_exists(s3_bucket, "test.txt")

def test_download(s3_client, s3_bucket):
    service = S3Service()
    service.client = s3_client
    # Setup for this specific test
    s3_client.put_object(Bucket=s3_bucket, Key="test.txt", Body=b"data")
    service.download_file(s3_bucket, "test.txt", local_path)
    assert local_path.exists()
```

### 8. Mock External Dependencies

```python
# Good - mock external AWS calls
def test_bedrock_invoke(bedrock_client):
    service = BedrockService()
    service.client = bedrock_client

    # Mock response
    bedrock_client.invoke_model.return_value = {...}

    result = service.invoke(messages=[...])
    assert result is not None
```

### 9. Test Coverage Goals

- **Critical Paths**: 100% coverage
- **Service Layer**: 90-100% coverage
- **Operators**: 85-95% coverage
- **DAG Files**: 80-90% coverage
- **Overall Project**: 80%+ coverage

### 10. Continuous Testing

```bash
# Watch mode - re-run tests on file changes
pytest-watch tests/

# Or use entr
find src tests -name "*.py" | entr pytest tests/
```

---

## Troubleshooting

### Common Issues

#### Issue: Import Errors

```bash
# Make sure you're in the project root
cd /home/user/airflow-demo

# Install in editable mode
pip install -e .
```

#### Issue: Fixtures Not Found

```python
# Make sure conftest.py is in the right location
tests/
  conftest.py  # ← Root conftest
  unit/
    conftest.py  # ← Optional unit-specific fixtures
```

#### Issue: Mocked Services Not Working

```python
# Make sure to patch at the point of use, not definition
# Bad
@patch("boto3.client")

# Good
@patch("src.airflow_demo.services.s3_service.boto3.client")
```

---

## Summary

TDD is a powerful approach for building reliable Airflow pipelines:

1. **Write tests first** - Define behavior before implementation
2. **Start simple** - Make tests pass with minimal code
3. **Refactor confidently** - Improve code with test safety net
4. **Test at multiple levels** - Unit, integration, and E2E
5. **Use fixtures** - Share common setup across tests
6. **Mock external services** - Fast, reliable tests
7. **Aim for high coverage** - But don't sacrifice quality for numbers

Happy testing!
