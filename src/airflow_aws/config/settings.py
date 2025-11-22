"""Application settings using Pydantic for configuration management."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSSettings(BaseSettings):
    """AWS service configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AWS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    region: str = Field(default="us-east-1", description="AWS region")
    account_id: Optional[str] = Field(default=None, description="AWS account ID")

    # S3 Configuration
    s3_bucket_data: str = Field(default="airflow-data", description="S3 data bucket")
    s3_bucket_logs: str = Field(default="airflow-logs", description="S3 logs bucket")
    s3_prefix: str = Field(default="airflow/", description="S3 key prefix")

    # Secrets Manager Configuration
    secrets_backend_enabled: bool = Field(default=True, description="Use Secrets Manager")
    secrets_prefix: str = Field(default="airflow/", description="Secrets path prefix")

    # IAM Configuration
    airflow_execution_role: Optional[str] = Field(
        default=None, description="Airflow execution role ARN"
    )

    # Bedrock Configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock Claude model ID",
    )
    bedrock_region: str = Field(default="us-east-1", description="Bedrock region")


class AirflowSettings(BaseSettings):
    """Airflow configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AIRFLOW__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    home: str = Field(default="/opt/airflow", description="AIRFLOW_HOME path")
    dags_folder: str = Field(default="dags", description="DAGs folder path")
    plugins_folder: str = Field(default="plugins", description="Plugins folder path")

    # Database
    database_conn: str = Field(
        default="sqlite:////tmp/airflow.db", description="Airflow database connection"
    )

    # Executor
    executor: str = Field(default="LocalExecutor", description="Airflow executor")

    # Logging
    base_log_folder: str = Field(default="logs", description="Base log folder")
    remote_logging: bool = Field(default=False, description="Enable remote S3 logging")
    remote_log_conn_id: str = Field(default="aws_default", description="S3 logging connection")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: str = Field(default="local", description="Environment (local/dev/prod)")
    debug: bool = Field(default=False, description="Debug mode")

    # AWS Settings
    aws: AWSSettings = Field(default_factory=AWSSettings)

    # Airflow Settings
    airflow: AirflowSettings = Field(default_factory=AirflowSettings)


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
