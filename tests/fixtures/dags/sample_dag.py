"""
Sample DAG demonstrating S3 + Bedrock integration.

This DAG shows a complete data pipeline:
1. Read documents from S3
2. Analyze with Bedrock
3. Write results back to S3
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def read_from_s3(**context):
    """Read document from S3."""
    from src.airflow_demo.services.s3_service import S3Service

    s3_service = S3Service()
    bucket = context["params"]["bucket"]
    key = context["params"]["input_key"]

    data = s3_service.read_json(bucket, key)
    context["ti"].xcom_push(key="document_data", value=data)
    return f"Read document from s3://{bucket}/{key}"


def analyze_with_bedrock(**context):
    """Analyze document using Bedrock."""
    from src.airflow_demo.services.bedrock_service import BedrockService

    bedrock_service = BedrockService()

    # Get document from previous task
    document_data = context["ti"].xcom_pull(key="document_data")
    document_text = document_data.get("content", "")

    # Analyze
    analysis = bedrock_service.analyze_document(
        document_text, "Summarize this document and identify key topics."
    )

    # Store result
    context["ti"].xcom_push(key="analysis_result", value=analysis)
    return "Document analyzed successfully"


def write_to_s3(**context):
    """Write analysis results to S3."""
    from src.airflow_demo.services.s3_service import S3Service

    s3_service = S3Service()

    bucket = context["params"]["bucket"]
    output_key = context["params"]["output_key"]

    # Get analysis result
    analysis = context["ti"].xcom_pull(key="analysis_result")
    document_data = context["ti"].xcom_pull(key="document_data")

    # Create result object
    result = {
        "original_document": document_data,
        "analysis": analysis,
        "analyzed_at": datetime.now().isoformat(),
        "dag_run_id": context["run_id"],
    }

    # Write to S3
    s3_uri = s3_service.write_json(result, bucket, output_key, indent=2)
    return f"Results written to {s3_uri}"


with DAG(
    "document_analysis_pipeline",
    default_args=default_args,
    description="Analyze documents from S3 using Bedrock",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["example", "s3", "bedrock", "ai"],
    params={
        "bucket": "my-data-bucket",
        "input_key": "input/document.json",
        "output_key": "output/analysis.json",
    },
) as dag:
    read_task = PythonOperator(
        task_id="read_from_s3",
        python_callable=read_from_s3,
    )

    analyze_task = PythonOperator(
        task_id="analyze_with_bedrock",
        python_callable=analyze_with_bedrock,
    )

    write_task = PythonOperator(
        task_id="write_to_s3",
        python_callable=write_to_s3,
    )

    read_task >> analyze_task >> write_task
