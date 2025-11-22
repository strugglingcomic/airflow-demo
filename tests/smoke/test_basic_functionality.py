"""Smoke tests to verify basic functionality of our implementation."""

import json
import pytest


@pytest.mark.unit
def test_settings_import():
    """Verify settings can be imported and instantiated."""
    from src.airflow_aws.config.settings import Settings, get_settings

    settings = get_settings()
    assert settings is not None
    assert settings.aws.region == "us-east-1"
    assert settings.environment in ["local", "test"]


@pytest.mark.unit
@pytest.mark.aws
@pytest.mark.s3
def test_s3_service_basic_operations(mock_aws_services, s3_bucket, tmp_path):
    """Test basic S3 service operations."""
    from src.airflow_aws.services.s3_service import S3Service

    service = S3Service(bucket=s3_bucket)

    # Test upload
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello S3")
    s3_uri = service.upload_file(test_file, "test.txt")
    assert s3_uri == f"s3://{s3_bucket}/test.txt"

    # Test exists
    assert service.object_exists("test.txt") is True
    assert service.object_exists("nonexistent.txt") is False

    # Test JSON operations
    data = {"test": "data", "number": 42}
    service.write_json(data, "data.json")
    result = service.read_json("data.json")
    assert result == data

    # Test list
    keys = service.list_objects()
    assert "test.txt" in keys
    assert "data.json" in keys


@pytest.mark.unit
def test_bedrock_service_initialization(mock_aws_services):
    """Test Bedrock service can be initialized."""
    from src.airflow_aws.services.bedrock_service import BedrockService

    service = BedrockService()
    assert service is not None
    assert service.region == "us-east-1"
    assert "claude" in service.model_id.lower()


@pytest.mark.unit
def test_secrets_service_basic_operations(mock_aws_services, secrets_client):
    """Test basic Secrets Manager operations."""
    from src.airflow_aws.services.secrets_service import SecretsService

    # Create test secrets
    secrets_client.create_secret(
        Name="airflow/variables/test_var",
        SecretString="test_value"
    )
    secrets_client.create_secret(
        Name="airflow/connections/aws_default",
        SecretString=json.dumps({"conn_type": "aws", "region": "us-east-1"})
    )

    service = SecretsService()

    # Test get secret
    secret = service.get_secret("airflow/variables/test_var", parse_json=False)
    assert secret == "test_value"

    # Test get JSON secret
    connection = service.get_secret("airflow/connections/aws_default", parse_json=True)
    assert isinstance(connection, dict)
    assert connection["conn_type"] == "aws"


@pytest.mark.unit
def test_bedrock_hook_import():
    """Test Bedrock hook can be imported."""
    from plugins.hooks.bedrock_hook import BedrockHook

    # Just verify it imports successfully
    assert BedrockHook is not None


@pytest.mark.unit
def test_bedrock_operators_import():
    """Test Bedrock operators can be imported."""
    from plugins.operators.bedrock_operator import (
        BedrockClaudeOperator,
        BedrockDocumentAnalysisOperator,
    )

    # Just verify they import successfully
    assert BedrockClaudeOperator is not None
    assert BedrockDocumentAnalysisOperator is not None


@pytest.mark.unit
def test_example_dag_imports():
    """Test example DAG can be imported without errors."""
    import sys
    sys.path.insert(0, "/home/user/airflow-demo")

    from dags.examples.example_bedrock_claude import dag

    assert dag is not None
    assert dag.dag_id == "example_bedrock_claude"
    assert len(dag.tasks) == 7


@pytest.mark.unit
@pytest.mark.s3
def test_s3_service_error_handling(mock_aws_services, s3_bucket):
    """Test S3 service error handling."""
    from src.airflow_aws.services.s3_service import (
        S3Service,
        S3ObjectNotFoundError,
    )

    service = S3Service(bucket=s3_bucket)

    # Test reading non-existent file
    with pytest.raises(S3ObjectNotFoundError):
        service.read_json("nonexistent.json")

    # Test downloading non-existent file
    with pytest.raises(S3ObjectNotFoundError):
        service.download_file("nonexistent.txt", "/tmp/test.txt")


@pytest.mark.unit
def test_secrets_service_error_handling(mock_aws_services):
    """Test Secrets Manager error handling."""
    from src.airflow_aws.services.secrets_service import (
        SecretsService,
        SecretNotFoundError,
    )

    service = SecretsService()

    # Test getting non-existent secret
    with pytest.raises(SecretNotFoundError):
        service.get_secret("nonexistent/secret")
