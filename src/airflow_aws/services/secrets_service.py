"""Secrets Manager service layer."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SecretsServiceError(Exception):
    """Base exception for Secrets service errors."""

    pass


class SecretNotFoundError(SecretsServiceError):
    """Exception raised when secret is not found."""

    pass


class SecretsService:
    """Service for AWS Secrets Manager operations."""

    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize Secrets service.

        Args:
            region_name: AWS region
        """
        self.settings = get_settings()
        self.region = region_name or self.settings.aws.region
        self.client = boto3.client("secretsmanager", region_name=self.region)
        logger.info(f"SecretsService initialized for region: {self.region}")

    def get_secret(
        self,
        secret_name: str,
        parse_json: bool = True,
    ) -> Union[str, Dict[str, Any]]:
        """
        Retrieve secret value.

        Args:
            secret_name: Name of the secret
            parse_json: Parse as JSON if True

        Returns:
            Secret value (string or dict)

        Raises:
            SecretNotFoundError: If secret not found
            SecretsServiceError: If access denied or other error
        """
        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            if "SecretString" in response:
                secret = response["SecretString"]
                if parse_json:
                    try:
                        return json.loads(secret)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Secret {secret_name} is not valid JSON, returning as string"
                        )
                        return secret
                return secret
            else:
                # Binary secret
                return response["SecretBinary"]

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{secret_name}' not found") from e
            elif error_code == "AccessDeniedException":
                raise SecretsServiceError(
                    f"Access denied to secret '{secret_name}'"
                ) from e
            else:
                logger.error(f"Failed to get secret {secret_name}: {e}")
                raise SecretsServiceError(f"Failed to get secret: {e}") from e

    def get_airflow_connection(self, conn_id: str) -> Dict[str, Any]:
        """
        Get Airflow connection from Secrets Manager.

        Args:
            conn_id: Airflow connection ID

        Returns:
            Connection details as dict

        Raises:
            SecretNotFoundError: If connection not found
        """
        secret_name = f"{self.settings.aws.secrets_prefix}connections/{conn_id}"
        logger.info(f"Retrieving Airflow connection: {conn_id}")
        return self.get_secret(secret_name, parse_json=True)

    def get_airflow_variable(self, variable_key: str) -> str:
        """
        Get Airflow variable from Secrets Manager.

        Args:
            variable_key: Variable key

        Returns:
            Variable value as string

        Raises:
            SecretNotFoundError: If variable not found
        """
        secret_name = f"{self.settings.aws.secrets_prefix}variables/{variable_key}"
        logger.info(f"Retrieving Airflow variable: {variable_key}")
        return self.get_secret(secret_name, parse_json=False)

    def create_secret(
        self,
        secret_name: str,
        secret_value: Union[str, Dict[str, Any]],
        description: str = "",
    ) -> str:
        """
        Create a new secret.

        Args:
            secret_name: Name of the secret
            secret_value: Secret value (string or dict)
            description: Secret description

        Returns:
            Secret ARN

        Raises:
            SecretsServiceError: If creation fails
        """
        if isinstance(secret_value, dict):
            secret_value = json.dumps(secret_value)

        try:
            response = self.client.create_secret(
                Name=secret_name,
                Description=description,
                SecretString=secret_value,
            )
            logger.info(f"Secret created: {secret_name}")
            return response["ARN"]
        except ClientError as e:
            logger.error(f"Failed to create secret {secret_name}: {e}")
            raise SecretsServiceError(f"Failed to create secret: {e}") from e

    def update_secret(
        self,
        secret_name: str,
        secret_value: Union[str, Dict[str, Any]],
    ) -> str:
        """
        Update existing secret.

        Args:
            secret_name: Name of the secret
            secret_value: New secret value

        Returns:
            Secret ARN

        Raises:
            SecretsServiceError: If update fails
        """
        if isinstance(secret_value, dict):
            secret_value = json.dumps(secret_value)

        try:
            response = self.client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value,
            )
            logger.info(f"Secret updated: {secret_name}")
            return response["ARN"]
        except ClientError as e:
            logger.error(f"Failed to update secret {secret_name}: {e}")
            raise SecretsServiceError(f"Failed to update secret: {e}") from e

    def delete_secret(
        self,
        secret_name: str,
        force_delete: bool = False,
    ) -> None:
        """
        Delete secret from Secrets Manager.

        Args:
            secret_name: Name of the secret
            force_delete: If True, delete immediately without recovery window

        Raises:
            SecretsServiceError: If deletion fails
        """
        try:
            if force_delete:
                self.client.delete_secret(
                    SecretId=secret_name,
                    ForceDeleteWithoutRecovery=True,
                )
                logger.info(f"Secret deleted immediately: {secret_name}")
            else:
                self.client.delete_secret(
                    SecretId=secret_name,
                    RecoveryWindowInDays=7,
                )
                logger.info(f"Secret scheduled for deletion: {secret_name} (7 day recovery)")
        except ClientError as e:
            logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise SecretsServiceError(f"Failed to delete secret: {e}") from e

    def list_secrets(
        self,
        name_prefix: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List secrets in Secrets Manager.

        Args:
            name_prefix: Optional prefix to filter secrets

        Returns:
            List of secret metadata dicts

        Raises:
            SecretsServiceError: If listing fails
        """
        try:
            paginator = self.client.get_paginator("list_secrets")

            filters = []
            if name_prefix:
                filters.append({"Key": "name", "Values": [name_prefix]})

            secrets = []
            for page in paginator.paginate(Filters=filters):
                secrets.extend(page.get("SecretList", []))

            logger.info(f"Listed {len(secrets)} secrets")
            return secrets
        except ClientError as e:
            logger.error(f"Failed to list secrets: {e}")
            raise SecretsServiceError(f"Failed to list secrets: {e}") from e
