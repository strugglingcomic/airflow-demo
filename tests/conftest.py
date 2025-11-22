"""
Root conftest.py for pytest configuration and shared fixtures.

This module provides:
- AWS service mocks (S3, Secrets Manager, Bedrock, IAM)
- Airflow test fixtures (DAG bag, task instances, execution context)
- Test data fixtures (sample files, JSON payloads)
- Utility fixtures (temp directories, freezegun, etc.)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, Mock

import boto3
import pytest
from airflow.models import DAG, DagBag, TaskInstance
from airflow.utils.dates import days_ago
from airflow.utils.state import DagRunState, TaskInstanceState
from airflow.utils.types import DagRunType
from faker import Faker
from freezegun import freeze_time
from moto import mock_aws

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set Airflow home for testing
    os.environ["AIRFLOW_HOME"] = str(Path(__file__).parent.parent / "test_airflow_home")
    os.environ["AIRFLOW__CORE__UNIT_TEST_MODE"] = "True"
    os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "False"
    os.environ["AIRFLOW__CORE__LOAD_DEFAULT_CONNECTIONS"] = "False"
    os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = str(
        Path(__file__).parent.parent / "tests" / "fixtures" / "dags"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their path."""
    for item in items:
        # Add markers based on test path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Add AWS service markers
        if "s3" in str(item.fspath).lower() or "s3" in item.name.lower():
            item.add_marker(pytest.mark.s3)
            item.add_marker(pytest.mark.aws)
        if "secrets" in str(item.fspath).lower() or "secrets" in item.name.lower():
            item.add_marker(pytest.mark.secrets)
            item.add_marker(pytest.mark.aws)
        if "bedrock" in str(item.fspath).lower() or "bedrock" in item.name.lower():
            item.add_marker(pytest.mark.bedrock)
            item.add_marker(pytest.mark.aws)
        if "dag" in str(item.fspath).lower() or "dag" in item.name.lower():
            item.add_marker(pytest.mark.dag)


# ============================================================================
# AWS MOCK FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    yield
    # Cleanup
    for key in [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SECURITY_TOKEN",
        "AWS_SESSION_TOKEN",
    ]:
        os.environ.pop(key, None)


@pytest.fixture(scope="function")
def mock_aws_services(aws_credentials):
    """
    Mock all AWS services using moto.

    This fixture provides a complete AWS environment mock including:
    - S3
    - Secrets Manager
    - Bedrock
    - IAM
    """
    with mock_aws():
        yield


@pytest.fixture
def s3_client(mock_aws_services):
    """Provide a mocked S3 client."""
    return boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def s3_resource(mock_aws_services):
    """Provide a mocked S3 resource."""
    return boto3.resource("s3", region_name="us-east-1")


@pytest.fixture
def secrets_client(mock_aws_services):
    """Provide a mocked Secrets Manager client."""
    return boto3.client("secretsmanager", region_name="us-east-1")


@pytest.fixture
def bedrock_client(mock_aws_services):
    """Provide a mocked Bedrock Runtime client."""
    return boto3.client("bedrock-runtime", region_name="us-east-1")


@pytest.fixture
def iam_client(mock_aws_services):
    """Provide a mocked IAM client."""
    return boto3.client("iam", region_name="us-east-1")


# ============================================================================
# S3 FIXTURES
# ============================================================================


@pytest.fixture
def s3_bucket(s3_client):
    """Create a test S3 bucket."""
    bucket_name = "test-airflow-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    return bucket_name


@pytest.fixture
def s3_bucket_with_data(s3_client, s3_bucket, sample_json_data):
    """Create an S3 bucket with sample data."""
    # Upload various test files
    s3_client.put_object(
        Bucket=s3_bucket, Key="data/sample.json", Body=json.dumps(sample_json_data)
    )
    s3_client.put_object(
        Bucket=s3_bucket, Key="data/sample.txt", Body="Hello, World!"
    )
    s3_client.put_object(
        Bucket=s3_bucket, Key="data/nested/file.json", Body='{"nested": true}'
    )
    # Add empty folder marker
    s3_client.put_object(Bucket=s3_bucket, Key="empty_folder/", Body="")
    return s3_bucket


@pytest.fixture
def s3_versioned_bucket(s3_client):
    """Create a test S3 bucket with versioning enabled."""
    bucket_name = "test-versioned-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    return bucket_name


# ============================================================================
# SECRETS MANAGER FIXTURES
# ============================================================================


@pytest.fixture
def sample_secrets(secrets_client) -> Dict[str, str]:
    """Create sample secrets in Secrets Manager."""
    secrets = {
        "airflow/connections/aws_default": json.dumps(
            {
                "conn_type": "aws",
                "login": "AKIAIOSFODNN7EXAMPLE",
                "password": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            }
        ),
        "airflow/variables/bedrock_model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "airflow/variables/s3_bucket": "my-data-bucket",
        "database/password": "super-secret-password",
        "api/key": "1234567890abcdef",
    }

    created_secrets = {}
    for name, value in secrets.items():
        secrets_client.create_secret(Name=name, SecretString=value)
        created_secrets[name] = value

    return created_secrets


# ============================================================================
# BEDROCK FIXTURES
# ============================================================================


@pytest.fixture
def bedrock_model_id() -> str:
    """Return the Bedrock model ID for testing."""
    return "anthropic.claude-3-5-sonnet-20241022-v2:0"


@pytest.fixture
def bedrock_streaming_response():
    """Mock Bedrock streaming response."""
    return {
        "ResponseMetadata": {
            "RequestId": "test-request-id",
            "HTTPStatusCode": 200,
        },
        "body": MagicMock(
            __iter__=lambda self: iter(
                [
                    {
                        "contentBlockStart": {
                            "start": {"text": ""},
                            "contentBlockIndex": 0,
                        }
                    },
                    {"contentBlockDelta": {"delta": {"text": "Hello"}, "contentBlockIndex": 0}},
                    {"contentBlockDelta": {"delta": {"text": " from"}, "contentBlockIndex": 0}},
                    {
                        "contentBlockDelta": {
                            "delta": {"text": " Claude!"},
                            "contentBlockIndex": 0,
                        }
                    },
                    {
                        "contentBlockStop": {"contentBlockIndex": 0},
                        "messageStop": {"stopReason": "end_turn"},
                    },
                ]
            )
        ),
    }


@pytest.fixture
def bedrock_non_streaming_response():
    """Mock Bedrock non-streaming response."""
    return {
        "ResponseMetadata": {
            "RequestId": "test-request-id",
            "HTTPStatusCode": 200,
        },
        "body": {
            "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello from Claude!"}],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        },
    }


# ============================================================================
# AIRFLOW FIXTURES
# ============================================================================


@pytest.fixture
def sample_dag():
    """Create a simple test DAG."""
    dag = DAG(
        dag_id="test_dag",
        start_date=days_ago(1),
        schedule_interval="@daily",
        catchup=False,
        tags=["test"],
    )
    return dag


@pytest.fixture
def execution_date():
    """Return a fixed execution date for testing."""
    return datetime(2024, 1, 1, 0, 0, 0)


@pytest.fixture
def dag_run(sample_dag, execution_date):
    """Create a test DagRun."""
    from airflow.models import DagRun

    dag_run = DagRun(
        dag_id=sample_dag.dag_id,
        run_id=f"test_run_{execution_date.isoformat()}",
        execution_date=execution_date,
        start_date=execution_date,
        run_type=DagRunType.MANUAL,
        state=DagRunState.RUNNING,
    )
    return dag_run


@pytest.fixture
def task_instance(sample_dag, execution_date):
    """Create a test TaskInstance."""
    from airflow.operators.empty import EmptyOperator

    task = EmptyOperator(task_id="test_task", dag=sample_dag)
    ti = TaskInstance(task=task, execution_date=execution_date)
    ti.state = TaskInstanceState.RUNNING
    return ti


@pytest.fixture
def airflow_context(sample_dag, dag_run, task_instance, execution_date):
    """Create a complete Airflow execution context."""
    return {
        "dag": sample_dag,
        "dag_run": dag_run,
        "task": task_instance.task,
        "task_instance": task_instance,
        "ti": task_instance,
        "execution_date": execution_date,
        "ds": execution_date.strftime("%Y-%m-%d"),
        "ds_nodash": execution_date.strftime("%Y%m%d"),
        "ts": execution_date.isoformat(),
        "ts_nodash": execution_date.strftime("%Y%m%dT%H%M%S"),
        "prev_execution_date": execution_date - timedelta(days=1),
        "next_execution_date": execution_date + timedelta(days=1),
        "params": {},
        "var": {"json": {}, "value": {}},
        "conf": {},
        "run_id": dag_run.run_id,
        "test_mode": True,
    }


@pytest.fixture
def dag_bag(tmp_path):
    """Create a DagBag for testing."""
    dags_folder = tmp_path / "dags"
    dags_folder.mkdir()
    return DagBag(dag_folder=str(dags_folder), include_examples=False)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def faker_instance():
    """Provide a Faker instance for generating test data."""
    fake = Faker()
    Faker.seed(12345)  # For reproducible tests
    return fake


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "id": 1,
        "name": "Test Record",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": {
            "value": 42,
            "tags": ["test", "sample", "data"],
            "metadata": {"source": "test", "version": "1.0"},
        },
        "items": [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"},
            {"id": 3, "value": "third"},
        ],
    }


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """id,name,value,timestamp
1,Alice,100,2024-01-01T00:00:00Z
2,Bob,200,2024-01-02T00:00:00Z
3,Charlie,300,2024-01-03T00:00:00Z
4,David,400,2024-01-04T00:00:00Z
5,Eve,500,2024-01-05T00:00:00Z
"""


@pytest.fixture
def sample_bedrock_request():
    """Sample Bedrock API request payload."""
    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, Claude!"}],
            }
        ],
        "temperature": 0.7,
        "top_p": 0.9,
    }


@pytest.fixture
def large_json_dataset(faker_instance):
    """Generate a large JSON dataset for performance testing."""
    return [
        {
            "id": i,
            "name": faker_instance.name(),
            "email": faker_instance.email(),
            "address": faker_instance.address(),
            "company": faker_instance.company(),
            "timestamp": faker_instance.date_time_this_year().isoformat(),
            "value": faker_instance.random_int(min=0, max=10000),
        }
        for i in range(1000)
    ]


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing."""
    file_path = temp_dir / "test_file.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def frozen_time():
    """Freeze time for deterministic testing."""
    with freeze_time("2024-01-01 12:00:00"):
        yield datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock()


@pytest.fixture
def env_vars():
    """Fixture to temporarily set environment variables."""
    old_env = os.environ.copy()

    def _set_env(**kwargs):
        os.environ.update(kwargs)

    yield _set_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(old_env)


# ============================================================================
# PERFORMANCE AND METRICS FIXTURES
# ============================================================================


@pytest.fixture
def performance_timer():
    """Measure execution time of code blocks."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()
            self.elapsed = self.end_time - self.start_time

    return Timer


@pytest.fixture
def metrics_collector():
    """Collect metrics during test execution."""

    class MetricsCollector:
        def __init__(self):
            self.metrics = {}

        def record(self, name: str, value: Any):
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(value)

        def get(self, name: str) -> List[Any]:
            return self.metrics.get(name, [])

        def average(self, name: str) -> float:
            values = self.get(name)
            return sum(values) / len(values) if values else 0.0

    return MetricsCollector()


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_airflow_db():
    """Clean up Airflow database after each test."""
    yield
    # Cleanup would go here if using a real database
    # For unit tests, we typically don't need cleanup


@pytest.fixture(autouse=True)
def reset_airflow_config():
    """Reset Airflow configuration after each test."""
    from airflow.configuration import conf

    # Store original config
    original_config = {}
    for section in conf.getsection("core"):
        original_config[section] = conf.get("core", section)

    yield

    # Restore original config
    # Note: In real tests, you might need to actually restore config
