"""
Test helper utilities for generating test data, mocks, and assertions.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from faker import Faker


class S3TestHelper:
    """Helper class for S3-related test utilities."""

    @staticmethod
    def create_s3_object(
        bucket: str,
        key: str,
        content: str = "",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a mock S3 object response."""
        return {
            "Bucket": bucket,
            "Key": key,
            "Body": content.encode() if isinstance(content, str) else content,
            "ContentLength": len(content) if isinstance(content, str) else len(content),
            "ContentType": "application/octet-stream",
            "ETag": f'"{hash(content)}"',
            "LastModified": datetime.now(),
            "Metadata": metadata or {},
            "StorageClass": "STANDARD",
        }

    @staticmethod
    def create_s3_list_response(bucket: str, keys: list[str], prefix: str = "") -> dict[str, Any]:
        """Create a mock S3 list objects response."""
        contents = [
            {
                "Key": key,
                "LastModified": datetime.now(),
                "ETag": f'"{hash(key)}"',
                "Size": 1024,
                "StorageClass": "STANDARD",
            }
            for key in keys
            if key.startswith(prefix)
        ]

        return {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "IsTruncated": False,
            "Contents": contents,
            "Name": bucket,
            "Prefix": prefix,
            "MaxKeys": 1000,
            "EncodingType": "url",
        }

    @staticmethod
    def create_multipart_upload_response(bucket: str, key: str) -> dict[str, Any]:
        """Create a mock multipart upload initiation response."""
        return {
            "Bucket": bucket,
            "Key": key,
            "UploadId": "test-upload-id-12345",
        }


class SecretsTestHelper:
    """Helper class for Secrets Manager test utilities."""

    @staticmethod
    def create_secret_response(
        secret_name: str, secret_value: str, version_id: str | None = None
    ) -> dict[str, Any]:
        """Create a mock GetSecretValue response."""
        return {
            "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{secret_name}",
            "Name": secret_name,
            "SecretString": secret_value,
            "VersionId": version_id or "AWSCURRENT",
            "CreatedDate": datetime.now(),
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

    @staticmethod
    def create_secret_versions_response(secret_name: str, versions: list[str]) -> dict[str, Any]:
        """Create a mock ListSecretVersionIds response."""
        return {
            "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{secret_name}",
            "Name": secret_name,
            "Versions": [
                {
                    "VersionId": version_id,
                    "VersionStages": ["AWSCURRENT"] if i == 0 else ["AWSPREVIOUS"],
                    "CreatedDate": datetime.now() - timedelta(days=i),
                }
                for i, version_id in enumerate(versions)
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

    @staticmethod
    def create_airflow_connection_secret(
        conn_type: str = "aws",
        login: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Create an Airflow connection secret in the expected format."""
        connection = {"conn_type": conn_type}
        if login:
            connection["login"] = login
        if password:
            connection["password"] = password
        if host:
            connection["host"] = host
        if port:
            connection["port"] = port
        if extra:
            connection["extra"] = extra
        return json.dumps(connection)


class BedrockTestHelper:
    """Helper class for Bedrock test utilities."""

    @staticmethod
    def create_invoke_response(
        content: str,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        input_tokens: int = 10,
        output_tokens: int = 20,
    ) -> dict[str, Any]:
        """Create a mock Bedrock invoke_model response."""
        return {
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HTTPStatusCode": 200,
            },
            "contentType": "application/json",
            "body": json.dumps(
                {
                    "id": "msg_test123",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": content}],
                    "model": model_id.split("/")[-1],
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                }
            ).encode(),
        }

    @staticmethod
    def create_streaming_chunks(text: str, chunk_size: int = 10) -> list[dict[str, Any]]:
        """Create mock streaming response chunks."""
        chunks = []

        # Start chunk
        chunks.append(
            {
                "contentBlockStart": {
                    "start": {"text": ""},
                    "contentBlockIndex": 0,
                }
            }
        )

        # Content chunks
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i : i + chunk_size]
            chunks.append(
                {
                    "contentBlockDelta": {
                        "delta": {"text": chunk_text},
                        "contentBlockIndex": 0,
                    }
                }
            )

        # End chunk
        chunks.append(
            {
                "contentBlockStop": {"contentBlockIndex": 0},
                "messageStop": {"stopReason": "end_turn"},
            }
        )

        return chunks

    @staticmethod
    def create_request_payload(
        message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Create a valid Bedrock API request payload."""
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": message}],
                }
            ],
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        return payload


class DataBuilder:
    """Builder class for creating complex test data structures."""

    def __init__(self):
        self.fake = Faker()
        Faker.seed(12345)

    def build_user(self, **overrides) -> dict[str, Any]:
        """Build a user record."""
        user = {
            "id": self.fake.uuid4(),
            "name": self.fake.name(),
            "email": self.fake.email(),
            "created_at": self.fake.date_time_this_year().isoformat(),
            "active": True,
        }
        user.update(overrides)
        return user

    def build_transaction(self, **overrides) -> dict[str, Any]:
        """Build a transaction record."""
        transaction = {
            "id": self.fake.uuid4(),
            "user_id": self.fake.uuid4(),
            "amount": round(self.fake.pyfloat(min_value=1, max_value=10000), 2),
            "currency": "USD",
            "timestamp": self.fake.date_time_this_year().isoformat(),
            "status": self.fake.random_element(["pending", "completed", "failed"]),
            "description": self.fake.sentence(),
        }
        transaction.update(overrides)
        return transaction

    def build_log_entry(self, **overrides) -> dict[str, Any]:
        """Build a log entry."""
        log_entry = {
            "timestamp": self.fake.date_time_this_year().isoformat(),
            "level": self.fake.random_element(["DEBUG", "INFO", "WARNING", "ERROR"]),
            "message": self.fake.sentence(),
            "logger": self.fake.word(),
            "thread": self.fake.random_int(min=1000, max=9999),
        }
        log_entry.update(overrides)
        return log_entry

    def build_dataset(self, builder_method: str, count: int = 10) -> list[dict[str, Any]]:
        """Build a list of records using the specified builder method."""
        method = getattr(self, builder_method)
        return [method() for _ in range(count)]


class AssertionHelper:
    """Helper class for common assertions in tests."""

    @staticmethod
    def assert_s3_object_exists(s3_client, bucket: str, key: str):
        """Assert that an S3 object exists."""
        try:
            s3_client.head_object(Bucket=bucket, Key=key)
        except s3_client.exceptions.NoSuchKey:
            raise AssertionError(f"S3 object s3://{bucket}/{key} does not exist") from None

    @staticmethod
    def assert_s3_object_not_exists(s3_client, bucket: str, key: str):
        """Assert that an S3 object does not exist."""
        try:
            s3_client.head_object(Bucket=bucket, Key=key)
            raise AssertionError(f"S3 object s3://{bucket}/{key} should not exist")
        except s3_client.exceptions.NoSuchKey:
            pass

    @staticmethod
    def assert_s3_object_content(s3_client, bucket: str, key: str, expected_content: str):
        """Assert S3 object content matches expected."""
        response = s3_client.get_object(Bucket=bucket, Key=key)
        actual_content = response["Body"].read().decode()
        assert (
            actual_content == expected_content
        ), f"Content mismatch. Expected: {expected_content}, Got: {actual_content}"

    @staticmethod
    def assert_json_structure(data: dict[str, Any], expected_keys: list[str]):
        """Assert that a JSON structure contains expected keys."""
        missing_keys = set(expected_keys) - set(data.keys())
        assert not missing_keys, f"Missing keys: {missing_keys}"

    @staticmethod
    def assert_bedrock_response_valid(response: dict[str, Any]):
        """Assert that a Bedrock response has the expected structure."""
        assert "ResponseMetadata" in response
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        body = (
            json.loads(response["body"])
            if isinstance(response["body"], bytes)
            else response["body"]
        )
        assert "content" in body
        assert isinstance(body["content"], list)
        assert len(body["content"]) > 0

    @staticmethod
    def assert_task_instance_success(task_instance):
        """Assert that a TaskInstance completed successfully."""
        from airflow.utils.state import TaskInstanceState

        assert (
            task_instance.state == TaskInstanceState.SUCCESS
        ), f"Task failed with state: {task_instance.state}"

    @staticmethod
    def assert_dag_run_success(dag_run):
        """Assert that a DagRun completed successfully."""
        from airflow.utils.state import DagRunState

        assert dag_run.state == DagRunState.SUCCESS, f"DAG run failed with state: {dag_run.state}"


class MockResponseBuilder:
    """Builder for creating mock AWS service responses."""

    @staticmethod
    def s3_error_response(error_code: str, message: str) -> Exception:
        """Create a mock S3 error response."""
        from botocore.exceptions import ClientError

        return ClientError(
            {
                "Error": {"Code": error_code, "Message": message},
                "ResponseMetadata": {"HTTPStatusCode": 400},
            },
            "GetObject",
        )

    @staticmethod
    def secrets_error_response(error_code: str, message: str) -> Exception:
        """Create a mock Secrets Manager error response."""
        from botocore.exceptions import ClientError

        return ClientError(
            {
                "Error": {"Code": error_code, "Message": message},
                "ResponseMetadata": {"HTTPStatusCode": 400},
            },
            "GetSecretValue",
        )

    @staticmethod
    def bedrock_error_response(error_code: str, message: str) -> Exception:
        """Create a mock Bedrock error response."""
        from botocore.exceptions import ClientError

        return ClientError(
            {
                "Error": {"Code": error_code, "Message": message},
                "ResponseMetadata": {"HTTPStatusCode": 400},
            },
            "InvokeModel",
        )


class TimeHelper:
    """Helper class for time-related test utilities."""

    @staticmethod
    def get_execution_dates(
        start_date: datetime, count: int = 5, interval_days: int = 1
    ) -> list[datetime]:
        """Generate a list of execution dates."""
        return [start_date + timedelta(days=i * interval_days) for i in range(count)]

    @staticmethod
    def parse_airflow_ds(ds: str) -> datetime:
        """Parse Airflow ds format to datetime."""
        return datetime.strptime(ds, "%Y-%m-%d")

    @staticmethod
    def format_airflow_ds(dt: datetime) -> str:
        """Format datetime to Airflow ds format."""
        return dt.strftime("%Y-%m-%d")


# ============================================================================
# CONTEXT MANAGERS FOR TESTING
# ============================================================================


class does_not_raise:
    """Context manager for asserting that code does not raise an exception."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            raise AssertionError(f"Unexpected exception raised: {exc_type.__name__}: {exc_val}")
        return True
