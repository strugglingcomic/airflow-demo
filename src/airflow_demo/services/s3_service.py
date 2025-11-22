"""
S3 Service for handling S3 operations in Airflow.

This module provides a high-level interface for S3 operations
with proper error handling and logging.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """Base exception for S3Service errors."""

    pass


class S3ObjectNotFoundError(S3ServiceError):
    """Exception raised when an S3 object is not found."""

    pass


class S3Service:
    """Service class for S3 operations."""

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        """
        Initialize S3 service.

        Args:
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
        """
        self.region_name = region_name
        self.client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        self.resource = boto3.resource(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        logger.info(f"S3Service initialized for region: {region_name}")

    def upload_file(
        self,
        file_path: Union[str, Path],
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_path: Path to the file to upload
            bucket: S3 bucket name
            key: S3 object key
            metadata: Optional metadata to attach to the object

        Returns:
            S3 URI of the uploaded object

        Raises:
            S3ServiceError: If upload fails
        """
        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_file(str(file_path), bucket, key, ExtraArgs=extra_args)
            logger.info(f"Uploaded file {file_path} to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
        except (ClientError, S3UploadFailedError, FileNotFoundError, OSError) as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise S3ServiceError(f"Upload failed: {e}") from e

    def download_file(self, bucket: str, key: str, local_path: Union[str, Path]) -> Path:
        """
        Download a file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local path to save the file

        Returns:
            Path to the downloaded file

        Raises:
            S3ObjectNotFoundError: If object doesn't exist
            S3ServiceError: If download fails
        """
        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(bucket, key, str(local_path))
            logger.info(f"Downloaded s3://{bucket}/{key} to {local_path}")
            return local_path
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            logger.error(f"Failed to download file from S3: {e}")
            raise S3ServiceError(f"Download failed: {e}") from e

    def read_json(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Read and parse a JSON file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Parsed JSON data

        Raises:
            S3ObjectNotFoundError: If object doesn't exist
            S3ServiceError: If read or parse fails
        """
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)
            logger.info(f"Read JSON from s3://{bucket}/{key}")
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            raise S3ServiceError(f"Failed to read JSON: {e}") from e
        except json.JSONDecodeError as e:
            raise S3ServiceError(f"Invalid JSON content: {e}") from e

    def write_json(
        self, data: Dict[str, Any], bucket: str, key: str, indent: Optional[int] = None
    ) -> str:
        """
        Write JSON data to S3.

        Args:
            data: Data to write
            bucket: S3 bucket name
            key: S3 object key
            indent: Optional indentation for JSON formatting

        Returns:
            S3 URI of the written object

        Raises:
            S3ServiceError: If write fails
        """
        try:
            content = json.dumps(data, indent=indent)
            self.client.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
            logger.info(f"Wrote JSON to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
        except (ClientError, TypeError) as e:
            logger.error(f"Failed to write JSON to S3: {e}")
            raise S3ServiceError(f"Write failed: {e}") from e

    def list_objects(
        self, bucket: str, prefix: str = "", max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in an S3 bucket.

        Args:
            bucket: S3 bucket name
            prefix: Prefix to filter objects
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata

        Raises:
            S3ServiceError: If listing fails
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket, Prefix=prefix, MaxKeys=max_keys
            )
            objects = response.get("Contents", [])
            logger.info(f"Listed {len(objects)} objects from s3://{bucket}/{prefix}")
            return objects
        except ClientError as e:
            logger.error(f"Failed to list objects: {e}")
            raise S3ServiceError(f"List failed: {e}") from e

    def object_exists(self, bucket: str, key: str) -> bool:
        """
        Check if an object exists in S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise S3ServiceError(f"Failed to check object existence: {e}") from e

    def delete_object(self, bucket: str, key: str) -> None:
        """
        Delete an object from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Raises:
            S3ServiceError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted s3://{bucket}/{key}")
        except ClientError as e:
            logger.error(f"Failed to delete object: {e}")
            raise S3ServiceError(f"Delete failed: {e}") from e

    def copy_object(
        self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str
    ) -> str:
        """
        Copy an object within S3.

        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key

        Returns:
            S3 URI of the destination object

        Raises:
            S3ServiceError: If copy fails
        """
        try:
            copy_source = {"Bucket": source_bucket, "Key": source_key}
            self.client.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
            logger.info(
                f"Copied s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}"
            )
            return f"s3://{dest_bucket}/{dest_key}"
        except ClientError as e:
            logger.error(f"Failed to copy object: {e}")
            raise S3ServiceError(f"Copy failed: {e}") from e

    def get_object_metadata(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Get metadata for an S3 object.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Object metadata

        Raises:
            S3ObjectNotFoundError: If object doesn't exist
            S3ServiceError: If metadata retrieval fails
        """
        try:
            response = self.client.head_object(Bucket=bucket, Key=key)
            return {
                "size": response["ContentLength"],
                "last_modified": response["LastModified"],
                "etag": response["ETag"],
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            raise S3ServiceError(f"Failed to get metadata: {e}") from e
