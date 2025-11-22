"""
Simple Hello World DAG demonstrating Claude/Bedrock integration.

This DAG contains a single task that invokes Claude to generate a greeting.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.airflow_demo.services.bedrock_service import BedrockService

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def hello_claude(**context):
    """Simple task that asks Claude to say hello."""
    bedrock_service = BedrockService()

    # Simple prompt for Claude
    response = bedrock_service.chat(
        prompt="Say hello and introduce yourself in one sentence.",
        max_tokens=100,
        temperature=0.7,
    )

    print(f"Claude says: {response}")
    return response


with DAG(
    "hello_claude",
    default_args=default_args,
    description="Simple hello world DAG using Claude via Bedrock",
    schedule_interval=None,  # Manual trigger only
    start_date=days_ago(1),
    catchup=False,
    tags=["example", "bedrock", "claude", "hello-world"],
) as dag:

    hello_task = PythonOperator(
        task_id="say_hello",
        python_callable=hello_claude,
    )
