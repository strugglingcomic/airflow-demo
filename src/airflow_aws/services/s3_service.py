"""S3 service layer for S3 operations."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """Base exception for S3 service errors."""

    pass


class S3ObjectNotFoundError(S3ServiceError):
    """Exception raised when S3 object is not found."""

    pass


class S3Service:
    """Service for S3 operations."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        """
        Initialize S3 service.

        Args:
            bucket: Default S3 bucket
            region_name: AWS region
        """
        self.settings = get_settings()
        self.bucket = bucket or self.settings.aws.s3_bucket_data
        self.region = region_name or self.settings.aws.region

        self.client = boto3.client("s3", region_name=self.region)
        self.resource = boto3.resource("s3", region_name=self.region)
        logger.info(f"S3Service initialized for bucket: {self.bucket}, region: {self.region}")

    def upload_file(
        self,
        file_path: Union[str, Path],
        key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to S3.

        Args:
            file_path: Local file path
            key: S3 object key
            bucket: S3 bucket (uses default if not provided)
            metadata: Optional metadata

        Returns:
            S3 URI of uploaded file

        Raises:
            S3ServiceError: If upload fails
        """
        bucket = bucket or self.bucket
        extra_args = {"Metadata": metadata} if metadata else {}

        try:
            self.client.upload_file(str(file_path), bucket, key, ExtraArgs=extra_args)
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"File uploaded successfully: {s3_uri}")
            return s3_uri
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise S3ServiceError(f"Failed to upload file: {e}") from e

    def download_file(
        self,
        key: str,
        file_path: Union[str, Path],
        bucket: Optional[str] = None,
    ) -> Path:
        """
        Download file from S3.

        Args:
            key: S3 object key
            file_path: Local file path
            bucket: S3 bucket

        Returns:
            Local file path

        Raises:
            S3ObjectNotFoundError: If object not found
            S3ServiceError: If download fails
        """
        bucket = bucket or self.bucket

        try:
            self.client.download_file(bucket, key, str(file_path))
            logger.info(f"File downloaded successfully from s3://{bucket}/{key}")
            return Path(file_path)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            logger.error(f"Failed to download file from S3: {e}")
            raise S3ServiceError(f"Failed to download file: {e}") from e

    def read_json(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Read JSON object from S3.

        Args:
            key: S3 object key
            bucket: S3 bucket

        Returns:
            Parsed JSON data

        Raises:
            S3ObjectNotFoundError: If object not found
            S3ServiceError: If read fails or invalid JSON
        """
        bucket = bucket or self.bucket

        try:
            obj = self.resource.Object(bucket, key)
            data = obj.get()["Body"].read().decode("utf-8")
            return json.loads(data)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            logger.error(f"Failed to read JSON from S3: {e}")
            raise S3ServiceError(f"Failed to read JSON: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in s3://{bucket}/{key}: {e}")
            raise S3ServiceError(f"Invalid JSON: {e}") from e

    def write_json(
        self,
        data: Dict[str, Any],
        key: str,
        bucket: Optional[str] = None,
    ) -> str:
        """
        Write JSON object to S3.

        Args:
            data: Data to write
            key: S3 object key
            bucket: S3 bucket

        Returns:
            S3 URI

        Raises:
            S3ServiceError: If write fails
        """
        bucket = bucket or self.bucket

        try:
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(data, indent=2),
                ContentType="application/json",
            )
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"JSON written successfully: {s3_uri}")
            return s3_uri
        except ClientError as e:
            logger.error(f"Failed to write JSON to S3: {e}")
            raise S3ServiceError(f"Failed to write JSON: {e}") from e

    def list_objects(
        self,
        prefix: str = "",
        bucket: Optional[str] = None,
    ) -> List[str]:
        """
        List objects with prefix.

        Args:
            prefix: S3 key prefix
            bucket: S3 bucket

        Returns:
            List of object keys

        Raises:
            S3ServiceError: If listing fails
        """
        bucket = bucket or self.bucket

        try:
            paginator = self.client.get_paginator("list_objects_v2")

            keys = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if "Contents" in page:
                    keys.extend([obj["Key"] for obj in page["Contents"]])

            logger.info(f"Listed {len(keys)} objects with prefix '{prefix}' in {bucket}")
            return keys
        except ClientError as e:
            logger.error(f"Failed to list objects in S3: {e}")
            raise S3ServiceError(f"Failed to list objects: {e}") from e

    def object_exists(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """
        Check if object exists.

        Args:
            key: S3 object key
            bucket: S3 bucket

        Returns:
            True if object exists
        """
        bucket = bucket or self.bucket

        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete_object(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> None:
        """
        Delete object from S3.

        Args:
            key: S3 object key
            bucket: S3 bucket

        Raises:
            S3ServiceError: If deletion fails
        """
        bucket = bucket or self.bucket

        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Object deleted: s3://{bucket}/{key}")
        except ClientError as e:
            logger.error(f"Failed to delete object from S3: {e}")
            raise S3ServiceError(f"Failed to delete object: {e}") from e

    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None,
    ) -> str:
        """
        Copy object within S3.

        Args:
            source_key: Source object key
            dest_key: Destination object key
            source_bucket: Source bucket (uses default if not provided)
            dest_bucket: Destination bucket (uses default if not provided)

        Returns:
            Destination S3 URI

        Raises:
            S3ServiceError: If copy fails
        """
        source_bucket = source_bucket or self.bucket
        dest_bucket = dest_bucket or self.bucket
        copy_source = {"Bucket": source_bucket, "Key": source_key}

        try:
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key,
            )
            dest_uri = f"s3://{dest_bucket}/{dest_key}"
            logger.info(
                f"Object copied from s3://{source_bucket}/{source_key} to {dest_uri}"
            )
            return dest_uri
        except ClientError as e:
            logger.error(f"Failed to copy object in S3: {e}")
            raise S3ServiceError(f"Failed to copy object: {e}") from e

    def get_object_metadata(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get object metadata.

        Args:
            key: S3 object key
            bucket: S3 bucket

        Returns:
            Object metadata

        Raises:
            S3ObjectNotFoundError: If object not found
            S3ServiceError: If retrieval fails
        """
        bucket = bucket or self.bucket

        try:
            response = self.client.head_object(Bucket=bucket, Key=key)
            metadata = {
                "content_length": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }
            return metadata
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket}/{key}") from e
            logger.error(f"Failed to get object metadata: {e}")
            raise S3ServiceError(f"Failed to get metadata: {e}") from e
