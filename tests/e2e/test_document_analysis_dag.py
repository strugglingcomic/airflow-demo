"""
End-to-end tests for document analysis DAG.

These tests demonstrate:
1. Full DAG execution testing
2. Task dependency verification
3. XCom data flow testing
4. Integration with AWS services in DAG context
"""

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from airflow.models import DagBag, TaskInstance
from airflow.utils.state import DagRunState, TaskInstanceState

from src.airflow_demo.services.bedrock_service import BedrockService
from src.airflow_demo.services.s3_service import S3Service
from tests.utils.test_helpers import BedrockTestHelper


@pytest.fixture
def dag_bag():
    """Load the DAG bag with our test DAGs."""
    dags_folder = Path(__file__).parent.parent / "fixtures" / "dags"
    return DagBag(dag_folder=str(dags_folder), include_examples=False)


@pytest.fixture
def document_analysis_dag(dag_bag):
    """Get the document analysis DAG."""
    dag = dag_bag.get_dag("document_analysis_pipeline")
    assert dag is not None, "DAG not found in DagBag"
    return dag


@pytest.mark.e2e
@pytest.mark.dag
class TestDocumentAnalysisDAGStructure:
    """Test DAG structure and configuration."""

    def test_dag_loaded(self, document_analysis_dag):
        """Test that DAG is properly loaded."""
        assert document_analysis_dag is not None
        assert document_analysis_dag.dag_id == "document_analysis_pipeline"

    def test_dag_has_correct_tasks(self, document_analysis_dag):
        """Test that DAG has all expected tasks."""
        tasks = document_analysis_dag.tasks
        task_ids = [task.task_id for task in tasks]

        assert "read_from_s3" in task_ids
        assert "analyze_with_bedrock" in task_ids
        assert "write_to_s3" in task_ids
        assert len(tasks) == 3

    def test_dag_task_dependencies(self, document_analysis_dag):
        """Test that tasks have correct dependencies."""
        read_task = document_analysis_dag.get_task("read_from_s3")
        analyze_task = document_analysis_dag.get_task("analyze_with_bedrock")
        write_task = document_analysis_dag.get_task("write_to_s3")

        # Check downstream dependencies
        assert analyze_task in read_task.downstream_list
        assert write_task in analyze_task.downstream_list

        # Check upstream dependencies
        assert read_task in analyze_task.upstream_list
        assert analyze_task in write_task.upstream_list

    def test_dag_default_args(self, document_analysis_dag):
        """Test DAG default arguments."""
        assert document_analysis_dag.default_args["owner"] == "airflow"
        assert document_analysis_dag.default_args["retries"] == 1

    def test_dag_schedule(self, document_analysis_dag):
        """Test DAG schedule interval."""
        assert document_analysis_dag.schedule_interval == "@daily"
        assert document_analysis_dag.catchup is False

    def test_dag_tags(self, document_analysis_dag):
        """Test DAG has expected tags."""
        assert "s3" in document_analysis_dag.tags
        assert "bedrock" in document_analysis_dag.tags
        assert "ai" in document_analysis_dag.tags


@pytest.mark.e2e
@pytest.mark.dag
class TestDocumentAnalysisDAGExecution:
    """Test end-to-end DAG execution."""

    def test_read_from_s3_task(
        self,
        document_analysis_dag,
        airflow_context,
        s3_client,
        s3_bucket,
        sample_json_data,
    ):
        """Test read_from_s3 task execution."""
        # Setup S3 service and upload test data
        s3_service = S3Service()
        s3_service.client = s3_client

        test_document = {"content": "This is a test document about AI."}
        s3_service.write_json(test_document, s3_bucket, "input/test.json")

        # Get task
        task = document_analysis_dag.get_task("read_from_s3")

        # Update context with params
        airflow_context["params"] = {
            "bucket": s3_bucket,
            "input_key": "input/test.json",
            "output_key": "output/test.json",
        }

        # Execute task
        result = task.execute(context=airflow_context)

        # Verify
        assert "Read document" in result
        assert s3_bucket in result

        # Check XCom was pushed
        document_data = airflow_context["ti"].xcom_pull(key="document_data")
        assert document_data == test_document

    def test_analyze_with_bedrock_task(
        self,
        document_analysis_dag,
        airflow_context,
        bedrock_client,
        bedrock_model_id,
    ):
        """Test analyze_with_bedrock task execution."""
        # Mock XCom pull
        test_document = {"content": "AI is transforming business."}
        airflow_context["ti"].xcom_pull = lambda key: (
            test_document if key == "document_data" else None
        )

        # Mock Bedrock response
        analysis_result = "Summary: AI transformation in business."
        response_data = BedrockTestHelper.create_invoke_response(analysis_result)
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        # Patch BedrockService to use our mocked client
        with patch("src.airflow_demo.services.bedrock_service.boto3.client") as mock_boto:
            mock_boto.return_value = bedrock_client

            # Get and execute task
            task = document_analysis_dag.get_task("analyze_with_bedrock")
            result = task.execute(context=airflow_context)

            # Verify
            assert "analyzed successfully" in result

            # Check XCom was pushed
            analysis = airflow_context["ti"].xcom_pull(key="analysis_result")
            assert analysis is not None

    def test_write_to_s3_task(
        self,
        document_analysis_dag,
        airflow_context,
        s3_client,
        s3_bucket,
    ):
        """Test write_to_s3 task execution."""
        # Setup S3
        s3_service = S3Service()
        s3_service.client = s3_client

        # Mock XCom pulls
        test_document = {"content": "Test content"}
        test_analysis = "Test analysis result"

        def mock_xcom_pull(key):
            if key == "document_data":
                return test_document
            elif key == "analysis_result":
                return test_analysis
            return None

        airflow_context["ti"].xcom_pull = mock_xcom_pull
        airflow_context["params"] = {
            "bucket": s3_bucket,
            "input_key": "input/test.json",
            "output_key": "output/result.json",
        }

        # Patch S3Service to use our mocked client
        with patch("src.airflow_demo.services.s3_service.boto3.client") as mock_boto:
            mock_boto.return_value = s3_client

            # Execute task
            task = document_analysis_dag.get_task("write_to_s3")
            result = task.execute(context=airflow_context)

            # Verify
            assert "Results written" in result
            assert s3_bucket in result

            # Verify file was written to S3
            saved_data = s3_service.read_json(s3_bucket, "output/result.json")
            assert saved_data["analysis"] == test_analysis
            assert saved_data["original_document"] == test_document

    def test_full_dag_execution(
        self,
        document_analysis_dag,
        execution_date,
        s3_client,
        bedrock_client,
        s3_bucket,
        bedrock_model_id,
    ):
        """Test complete DAG execution from start to finish."""
        # Setup S3
        s3_service = S3Service()
        s3_service.client = s3_client

        # Upload test document
        test_document = {
            "content": "Artificial Intelligence is revolutionizing industries."
        }
        s3_service.write_json(test_document, s3_bucket, "input/full_test.json")

        # Mock Bedrock
        analysis_result = "AI is transforming various industries."
        response_data = BedrockTestHelper.create_invoke_response(analysis_result)
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        # Patch both services
        with patch("src.airflow_demo.services.s3_service.boto3.client") as mock_s3, patch(
            "src.airflow_demo.services.bedrock_service.boto3.client"
        ) as mock_bedrock:
            mock_s3.return_value = s3_client
            mock_bedrock.return_value = bedrock_client

            # Create DAG run
            from airflow.models import DagRun
            from airflow.utils.types import DagRunType

            dag_run = DagRun(
                dag_id=document_analysis_dag.dag_id,
                run_id=f"test_run_{execution_date.isoformat()}",
                execution_date=execution_date,
                start_date=execution_date,
                run_type=DagRunType.MANUAL,
            )

            # Execute tasks in order
            params = {
                "bucket": s3_bucket,
                "input_key": "input/full_test.json",
                "output_key": "output/full_test_result.json",
            }

            # Store XCom data
            xcom_data = {}

            # Task 1: Read from S3
            read_task = document_analysis_dag.get_task("read_from_s3")
            ti_read = TaskInstance(task=read_task, execution_date=execution_date)

            # Mock XCom for read task
            def mock_xcom_push_read(key, value):
                xcom_data[key] = value

            ti_read.xcom_push = mock_xcom_push_read

            context_read = {
                "ti": ti_read,
                "params": params,
                "execution_date": execution_date,
            }
            read_task.execute(context=context_read)

            # Task 2: Analyze with Bedrock
            analyze_task = document_analysis_dag.get_task("analyze_with_bedrock")
            ti_analyze = TaskInstance(task=analyze_task, execution_date=execution_date)

            def mock_xcom_pull_analyze(key):
                return xcom_data.get(key)

            def mock_xcom_push_analyze(key, value):
                xcom_data[key] = value

            ti_analyze.xcom_pull = mock_xcom_pull_analyze
            ti_analyze.xcom_push = mock_xcom_push_analyze

            context_analyze = {
                "ti": ti_analyze,
                "params": params,
                "execution_date": execution_date,
            }
            analyze_task.execute(context=context_analyze)

            # Task 3: Write to S3
            write_task = document_analysis_dag.get_task("write_to_s3")
            ti_write = TaskInstance(task=write_task, execution_date=execution_date)

            def mock_xcom_pull_write(key):
                return xcom_data.get(key)

            ti_write.xcom_pull = mock_xcom_pull_write

            context_write = {
                "ti": ti_write,
                "params": params,
                "execution_date": execution_date,
                "run_id": dag_run.run_id,
            }
            write_task.execute(context=context_write)

            # Verify final output
            result = s3_service.read_json(s3_bucket, "output/full_test_result.json")
            assert result["analysis"] is not None
            assert result["original_document"]["content"] == test_document["content"]


@pytest.mark.e2e
@pytest.mark.dag
class TestDocumentAnalysisDAGErrorHandling:
    """Test error handling in DAG execution."""

    def test_read_from_s3_missing_file(
        self,
        document_analysis_dag,
        airflow_context,
        s3_client,
        s3_bucket,
    ):
        """Test handling of missing S3 file."""
        from src.airflow_demo.services.s3_service import S3ObjectNotFoundError

        task = document_analysis_dag.get_task("read_from_s3")

        airflow_context["params"] = {
            "bucket": s3_bucket,
            "input_key": "missing/file.json",
            "output_key": "output/test.json",
        }

        # Patch S3Service
        with patch("src.airflow_demo.services.s3_service.boto3.client") as mock_boto:
            mock_boto.return_value = s3_client

            with pytest.raises(S3ObjectNotFoundError):
                task.execute(context=airflow_context)

    def test_analyze_with_bedrock_error(
        self,
        document_analysis_dag,
        airflow_context,
        bedrock_client,
    ):
        """Test handling of Bedrock errors."""
        from botocore.exceptions import ClientError

        from src.airflow_demo.services.bedrock_service import BedrockServiceError

        # Mock XCom
        airflow_context["ti"].xcom_pull = lambda key: (
            {"content": "Test"} if key == "document_data" else None
        )

        # Mock Bedrock error
        bedrock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )

        task = document_analysis_dag.get_task("analyze_with_bedrock")

        with patch("src.airflow_demo.services.bedrock_service.boto3.client") as mock_boto:
            mock_boto.return_value = bedrock_client

            with pytest.raises(BedrockServiceError):
                task.execute(context=airflow_context)


@pytest.mark.e2e
@pytest.mark.dag
class TestDocumentAnalysisDAGValidation:
    """Test DAG validation and best practices."""

    def test_dag_bag_has_no_import_errors(self, dag_bag):
        """Test that DAG bag has no import errors."""
        assert len(dag_bag.import_errors) == 0, f"Import errors: {dag_bag.import_errors}"

    def test_all_tasks_have_owners(self, document_analysis_dag):
        """Test that all tasks have owners defined."""
        for task in document_analysis_dag.tasks:
            assert task.owner is not None
            assert task.owner != ""

    def test_dag_has_description(self, document_analysis_dag):
        """Test that DAG has a description."""
        assert document_analysis_dag.description is not None
        assert len(document_analysis_dag.description) > 0

    def test_tasks_have_retries_configured(self, document_analysis_dag):
        """Test that tasks have retry configuration."""
        for task in document_analysis_dag.tasks:
            assert task.retries is not None
            assert task.retries >= 0

    def test_no_cycles_in_dag(self, document_analysis_dag):
        """Test that DAG has no cycles."""
        # Airflow would catch this, but explicit test is good
        from airflow.models.dag import DAG

        # If DAG loads successfully, it has no cycles
        assert isinstance(document_analysis_dag, DAG)

    def test_dag_params_are_documented(self, document_analysis_dag):
        """Test that DAG params are properly defined."""
        assert "bucket" in document_analysis_dag.params
        assert "input_key" in document_analysis_dag.params
        assert "output_key" in document_analysis_dag.params
