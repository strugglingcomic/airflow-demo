"""
Unit tests for S3Service.

These tests demonstrate TDD principles:
1. Tests are written to define expected behavior
2. Each test is isolated and uses mocks
3. Tests cover happy paths, edge cases, and error conditions
4. Tests are fast and don't require real AWS services
"""

import json
from pathlib import Path

import pytest
from src.airflow_demo.services.s3_service import (
    S3ObjectNotFoundError,
    S3Service,
    S3ServiceError,
)

from tests.utils.test_helpers import (
    AssertionHelper,
)


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceInitialization:
    """Test S3Service initialization."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        service = S3Service(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="us-west-2",
        )
        assert service.region_name == "us-west-2"
        assert service.client is not None
        assert service.resource is not None

    def test_init_without_credentials(self):
        """Test initialization without explicit credentials (uses default AWS config)."""
        service = S3Service(region_name="eu-west-1")
        assert service.region_name == "eu-west-1"
        assert service.client is not None

    def test_init_default_region(self):
        """Test initialization with default region."""
        service = S3Service()
        assert service.region_name == "us-east-1"


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceUploadFile:
    """Test S3Service.upload_file method."""

    def test_upload_file_success(self, s3_client, s3_bucket, temp_file):
        """Test successful file upload."""
        service = S3Service()
        service.client = s3_client

        result = service.upload_file(temp_file, s3_bucket, "uploads/test.txt")

        assert result == f"s3://{s3_bucket}/uploads/test.txt"
        AssertionHelper.assert_s3_object_exists(s3_client, s3_bucket, "uploads/test.txt")

    def test_upload_file_with_metadata(self, s3_client, s3_bucket, temp_file):
        """Test file upload with metadata."""
        service = S3Service()
        service.client = s3_client

        metadata = {"user": "test_user", "version": "1.0"}
        result = service.upload_file(temp_file, s3_bucket, "uploads/test.txt", metadata=metadata)

        assert result == f"s3://{s3_bucket}/uploads/test.txt"

        # Verify metadata was attached
        response = s3_client.head_object(Bucket=s3_bucket, Key="uploads/test.txt")
        assert response["Metadata"] == metadata

    def test_upload_file_path_as_string(self, s3_client, s3_bucket, temp_file):
        """Test upload with file path as string."""
        service = S3Service()
        service.client = s3_client

        result = service.upload_file(str(temp_file), s3_bucket, "test.txt")

        assert result == f"s3://{s3_bucket}/test.txt"

    def test_upload_file_failure(self, s3_client, temp_file):
        """Test upload failure handling."""
        service = S3Service()
        service.client = s3_client

        # Try to upload to non-existent bucket
        with pytest.raises(S3ServiceError, match="Upload failed"):
            service.upload_file(temp_file, "non-existent-bucket", "test.txt")


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceDownloadFile:
    """Test S3Service.download_file method."""

    def test_download_file_success(self, s3_client, s3_bucket_with_data, temp_dir):
        """Test successful file download."""
        service = S3Service()
        service.client = s3_client

        local_path = temp_dir / "downloaded.txt"
        result = service.download_file(s3_bucket_with_data, "data/sample.txt", local_path)

        assert result == local_path
        assert local_path.exists()
        assert local_path.read_text() == "Hello, World!"

    def test_download_file_creates_directory(self, s3_client, s3_bucket_with_data, temp_dir):
        """Test download creates parent directories if they don't exist."""
        service = S3Service()
        service.client = s3_client

        local_path = temp_dir / "nested" / "path" / "downloaded.txt"
        result = service.download_file(s3_bucket_with_data, "data/sample.txt", local_path)

        assert result == local_path
        assert local_path.exists()
        assert local_path.parent.exists()

    def test_download_file_not_found(self, s3_client, s3_bucket, temp_dir):
        """Test download of non-existent file."""
        service = S3Service()
        service.client = s3_client

        local_path = temp_dir / "downloaded.txt"

        with pytest.raises(S3ObjectNotFoundError, match="Object not found"):
            service.download_file(s3_bucket, "non-existent.txt", local_path)

    def test_download_file_path_as_string(self, s3_client, s3_bucket_with_data, temp_dir):
        """Test download with path as string."""
        service = S3Service()
        service.client = s3_client

        local_path = str(temp_dir / "downloaded.txt")
        result = service.download_file(s3_bucket_with_data, "data/sample.txt", local_path)

        assert result == Path(local_path)


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceReadJson:
    """Test S3Service.read_json method."""

    def test_read_json_success(self, s3_client, s3_bucket_with_data, sample_json_data):
        """Test successful JSON reading."""
        service = S3Service()
        service.client = s3_client

        result = service.read_json(s3_bucket_with_data, "data/sample.json")

        assert result == sample_json_data
        assert result["id"] == 1
        assert result["name"] == "Test Record"

    def test_read_json_not_found(self, s3_client, s3_bucket):
        """Test reading non-existent JSON file."""
        service = S3Service()
        service.client = s3_client

        with pytest.raises(S3ObjectNotFoundError, match="Object not found"):
            service.read_json(s3_bucket, "non-existent.json")

    def test_read_json_invalid_content(self, s3_client, s3_bucket):
        """Test reading file with invalid JSON content."""
        service = S3Service()
        service.client = s3_client

        # Upload invalid JSON
        s3_client.put_object(Bucket=s3_bucket, Key="invalid.json", Body=b"{invalid json}")

        with pytest.raises(S3ServiceError, match="Invalid JSON content"):
            service.read_json(s3_bucket, "invalid.json")

    def test_read_json_empty_object(self, s3_client, s3_bucket):
        """Test reading empty JSON object."""
        service = S3Service()
        service.client = s3_client

        s3_client.put_object(Bucket=s3_bucket, Key="empty.json", Body=b"{}")

        result = service.read_json(s3_bucket, "empty.json")
        assert result == {}


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceWriteJson:
    """Test S3Service.write_json method."""

    def test_write_json_success(self, s3_client, s3_bucket, sample_json_data):
        """Test successful JSON writing."""
        service = S3Service()
        service.client = s3_client

        result = service.write_json(sample_json_data, s3_bucket, "output.json")

        assert result == f"s3://{s3_bucket}/output.json"

        # Verify content
        response = s3_client.get_object(Bucket=s3_bucket, Key="output.json")
        content = json.loads(response["Body"].read().decode())
        assert content == sample_json_data

    def test_write_json_with_indent(self, s3_client, s3_bucket):
        """Test JSON writing with indentation."""
        service = S3Service()
        service.client = s3_client

        data = {"key": "value", "nested": {"a": 1}}
        service.write_json(data, s3_bucket, "formatted.json", indent=2)

        # Verify formatting
        response = s3_client.get_object(Bucket=s3_bucket, Key="formatted.json")
        content = response["Body"].read().decode()
        assert "\n" in content  # Should have newlines from indentation
        assert "  " in content  # Should have indentation

    def test_write_json_invalid_data(self, s3_client, s3_bucket):
        """Test writing non-serializable data."""
        service = S3Service()
        service.client = s3_client

        # Create non-serializable data
        class NonSerializable:
            pass

        data = {"obj": NonSerializable()}

        with pytest.raises(S3ServiceError, match="Write failed"):
            service.write_json(data, s3_bucket, "invalid.json")

    def test_write_json_to_nested_path(self, s3_client, s3_bucket):
        """Test writing JSON to nested S3 path."""
        service = S3Service()
        service.client = s3_client

        data = {"test": "data"}
        result = service.write_json(data, s3_bucket, "path/to/nested/output.json")

        assert result == f"s3://{s3_bucket}/path/to/nested/output.json"
        AssertionHelper.assert_s3_object_exists(s3_client, s3_bucket, "path/to/nested/output.json")


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceListObjects:
    """Test S3Service.list_objects method."""

    def test_list_objects_success(self, s3_client, s3_bucket_with_data):
        """Test successful object listing."""
        service = S3Service()
        service.client = s3_client

        result = service.list_objects(s3_bucket_with_data)

        assert len(result) > 0
        assert all("Key" in obj for obj in result)

    def test_list_objects_with_prefix(self, s3_client, s3_bucket_with_data):
        """Test object listing with prefix filter."""
        service = S3Service()
        service.client = s3_client

        result = service.list_objects(s3_bucket_with_data, prefix="data/")

        assert len(result) > 0
        assert all(obj["Key"].startswith("data/") for obj in result)

    def test_list_objects_empty_bucket(self, s3_client, s3_bucket):
        """Test listing objects in empty bucket."""
        service = S3Service()
        service.client = s3_client

        result = service.list_objects(s3_bucket)

        assert result == []

    def test_list_objects_with_max_keys(self, s3_client, s3_bucket):
        """Test listing with max_keys limit."""
        service = S3Service()
        service.client = s3_client

        # Upload multiple objects
        for i in range(10):
            s3_client.put_object(Bucket=s3_bucket, Key=f"file_{i}.txt", Body=b"test")

        result = service.list_objects(s3_bucket, max_keys=5)

        assert len(result) <= 5


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceObjectExists:
    """Test S3Service.object_exists method."""

    def test_object_exists_true(self, s3_client, s3_bucket_with_data):
        """Test checking existence of existing object."""
        service = S3Service()
        service.client = s3_client

        result = service.object_exists(s3_bucket_with_data, "data/sample.txt")

        assert result is True

    def test_object_exists_false(self, s3_client, s3_bucket):
        """Test checking existence of non-existent object."""
        service = S3Service()
        service.client = s3_client

        result = service.object_exists(s3_bucket, "non-existent.txt")

        assert result is False


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceDeleteObject:
    """Test S3Service.delete_object method."""

    def test_delete_object_success(self, s3_client, s3_bucket_with_data):
        """Test successful object deletion."""
        service = S3Service()
        service.client = s3_client

        # Verify object exists before deletion
        assert service.object_exists(s3_bucket_with_data, "data/sample.txt")

        service.delete_object(s3_bucket_with_data, "data/sample.txt")

        # Verify object no longer exists
        assert not service.object_exists(s3_bucket_with_data, "data/sample.txt")

    def test_delete_non_existent_object(self, s3_client, s3_bucket):
        """Test deleting non-existent object (should not raise error)."""
        service = S3Service()
        service.client = s3_client

        # S3 delete is idempotent - doesn't fail if object doesn't exist
        service.delete_object(s3_bucket, "non-existent.txt")


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceCopyObject:
    """Test S3Service.copy_object method."""

    def test_copy_object_success(self, s3_client, s3_bucket_with_data):
        """Test successful object copy."""
        service = S3Service()
        service.client = s3_client

        result = service.copy_object(
            s3_bucket_with_data, "data/sample.txt", s3_bucket_with_data, "copy/sample.txt"
        )

        assert result == f"s3://{s3_bucket_with_data}/copy/sample.txt"
        AssertionHelper.assert_s3_object_exists(s3_client, s3_bucket_with_data, "copy/sample.txt")

        # Verify content is the same
        original = s3_client.get_object(Bucket=s3_bucket_with_data, Key="data/sample.txt")
        copied = s3_client.get_object(Bucket=s3_bucket_with_data, Key="copy/sample.txt")
        assert original["Body"].read() == copied["Body"].read()

    def test_copy_object_across_buckets(self, s3_client, s3_bucket_with_data):
        """Test copying object across different buckets."""
        service = S3Service()
        service.client = s3_client

        # Create destination bucket
        dest_bucket = "dest-bucket"
        s3_client.create_bucket(Bucket=dest_bucket)

        result = service.copy_object(
            s3_bucket_with_data, "data/sample.txt", dest_bucket, "sample.txt"
        )

        assert result == f"s3://{dest_bucket}/sample.txt"
        AssertionHelper.assert_s3_object_exists(s3_client, dest_bucket, "sample.txt")

    def test_copy_non_existent_object(self, s3_client, s3_bucket):
        """Test copying non-existent object."""
        service = S3Service()
        service.client = s3_client

        with pytest.raises(S3ServiceError, match="Copy failed"):
            service.copy_object(s3_bucket, "non-existent.txt", s3_bucket, "copy.txt")


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceGetObjectMetadata:
    """Test S3Service.get_object_metadata method."""

    def test_get_metadata_success(self, s3_client, s3_bucket_with_data):
        """Test retrieving object metadata."""
        service = S3Service()
        service.client = s3_client

        metadata = service.get_object_metadata(s3_bucket_with_data, "data/sample.txt")

        assert "size" in metadata
        assert "last_modified" in metadata
        assert "etag" in metadata
        assert metadata["size"] == len("Hello, World!")

    def test_get_metadata_with_custom_metadata(self, s3_client, s3_bucket):
        """Test retrieving object with custom metadata."""
        service = S3Service()
        service.client = s3_client

        # Upload object with custom metadata
        custom_metadata = {"author": "test", "version": "1.0"}
        s3_client.put_object(
            Bucket=s3_bucket, Key="test.txt", Body=b"test", Metadata=custom_metadata
        )

        metadata = service.get_object_metadata(s3_bucket, "test.txt")

        assert metadata["metadata"] == custom_metadata

    def test_get_metadata_not_found(self, s3_client, s3_bucket):
        """Test getting metadata for non-existent object."""
        service = S3Service()
        service.client = s3_client

        with pytest.raises(S3ObjectNotFoundError, match="Object not found"):
            service.get_object_metadata(s3_bucket, "non-existent.txt")


# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================


@pytest.mark.unit
@pytest.mark.s3
class TestS3ServiceErrorHandling:
    """Test error handling in S3Service."""

    def test_handles_client_errors_gracefully(self, s3_client):
        """Test graceful handling of AWS client errors."""
        service = S3Service()
        service.client = s3_client

        # Test various error scenarios
        with pytest.raises(S3ServiceError):
            service.upload_file("/non/existent/file.txt", "bucket", "key")

    def test_custom_exception_hierarchy(self):
        """Test custom exception hierarchy."""
        assert issubclass(S3ObjectNotFoundError, S3ServiceError)
        assert issubclass(S3ServiceError, Exception)

    def test_error_messages_are_informative(self, s3_client, s3_bucket):
        """Test that error messages contain useful information."""
        service = S3Service()
        service.client = s3_client

        try:
            service.read_json(s3_bucket, "missing.json")
        except S3ObjectNotFoundError as e:
            assert "Object not found" in str(e)
            assert s3_bucket in str(e)
            assert "missing.json" in str(e)


@pytest.mark.unit
@pytest.mark.s3
@pytest.mark.slow
class TestS3ServicePerformance:
    """Performance-related tests for S3Service."""

    def test_bulk_upload_performance(self, s3_client, s3_bucket, temp_dir, performance_timer):
        """Test performance of bulk uploads."""
        service = S3Service()
        service.client = s3_client

        # Create multiple test files
        files = []
        for i in range(10):
            file_path = temp_dir / f"file_{i}.txt"
            file_path.write_text(f"Content {i}")
            files.append(file_path)

        with performance_timer as timer:
            for i, file_path in enumerate(files):
                service.upload_file(file_path, s3_bucket, f"uploads/file_{i}.txt")

        # Performance assertion - should complete in reasonable time
        assert timer.elapsed < 5.0  # 5 seconds for 10 files

    def test_list_large_number_of_objects(self, s3_client, s3_bucket, performance_timer):
        """Test listing performance with many objects."""
        service = S3Service()
        service.client = s3_client

        # Create many objects
        for i in range(100):
            s3_client.put_object(Bucket=s3_bucket, Key=f"file_{i:03d}.txt", Body=b"test")

        with performance_timer as timer:
            result = service.list_objects(s3_bucket)

        assert len(result) == 100
        assert timer.elapsed < 2.0  # Should be fast with moto
