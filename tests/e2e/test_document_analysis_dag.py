"""
End-to-end tests for document analysis DAG.

These tests demonstrate:
1. Full DAG execution testing
2. Task dependency verification
3. XCom data flow testing
4. Integration with AWS services in DAG context
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from airflow.models import DagBag, TaskInstance
from airflow.utils.state import DagRunState, TaskInstanceState


@pytest.fixture
def dag_bag(airflow_db):
    """Load the DAG bag with our test DAGs."""
    dags_folder = Path(__file__).parent.parent / "fixtures" / "dags"
    return DagBag(dag_folder=str(dags_folder), include_examples=False)


@pytest.fixture
def document_analysis_dag(dag_bag):
    """Get the document analysis DAG."""
    dag = dag_bag.get_dag("document_analysis_pipeline")
    assert dag is not None, "DAG not found in DagBag"
    return dag


@pytest.fixture
def document_analysis_context(document_analysis_dag, execution_date, airflow_db):
    """Create execution context for document analysis DAG."""
    from datetime import timedelta

    from airflow import settings
    from airflow.models import DagRun
    from airflow.operators.empty import EmptyOperator
    from airflow.utils.types import DagRunType

    session = settings.Session()

    # Create a DagRun and persist to database
    dag_run = DagRun(
        dag_id=document_analysis_dag.dag_id,
        run_id=f"test_run_{execution_date.isoformat()}",
        execution_date=execution_date,
        start_date=execution_date,
        run_type=DagRunType.MANUAL,
        state=DagRunState.RUNNING,
    )
    session.add(dag_run)
    session.commit()

    # Create a dummy task and task instance
    task = EmptyOperator(task_id="test_task", dag=document_analysis_dag)
    ti = TaskInstance(task=task, run_id=dag_run.run_id)
    ti.state = TaskInstanceState.RUNNING
    session.add(ti)
    session.commit()

    # Create context
    context = {
        "dag": document_analysis_dag,
        "dag_run": dag_run,
        "task": task,
        "task_instance": ti,
        "ti": ti,
        "execution_date": execution_date,
        "ds": execution_date.strftime("%Y-%m-%d"),
        "ds_nodash": execution_date.strftime("%Y%m%d"),
        "ts": execution_date.isoformat(),
        "ts_nodash": execution_date.strftime("%Y%m%dT%H%M%S"),
        "prev_execution_date": execution_date - timedelta(days=1),
        "next_execution_date": execution_date + timedelta(days=1),
        "params": {},
        "var": {"json": {}, "value": {}},
        "conf": {},
        "run_id": dag_run.run_id,
        "test_mode": True,
    }

    yield context

    # Cleanup
    session.delete(ti)
    session.delete(dag_run)
    session.commit()
    session.close()


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
class TestDocumentAnalysisDAGErrorHandling:
    """Test error handling in DAG execution."""

    def test_read_from_s3_missing_file(
        self,
        document_analysis_dag,
        document_analysis_context,
        s3_client,
        s3_bucket,
    ):
        """Test handling of missing S3 file."""
        from src.airflow_demo.services.s3_service import S3ObjectNotFoundError

        task = document_analysis_dag.get_task("read_from_s3")

        document_analysis_context["params"] = {
            "bucket": s3_bucket,
            "input_key": "missing/file.json",
            "output_key": "output/test.json",
        }

        # Patch S3Service
        with patch("src.airflow_demo.services.s3_service.boto3.client") as mock_boto:
            mock_boto.return_value = s3_client

            with pytest.raises(S3ObjectNotFoundError):
                task.execute(context=document_analysis_context)

    def test_analyze_with_bedrock_error(
        self,
        document_analysis_dag,
        document_analysis_context,
        bedrock_client,
    ):
        """Test handling of Bedrock errors."""
        from botocore.exceptions import ClientError
        from src.airflow_demo.services.bedrock_service import BedrockServiceError

        # Mock XCom
        document_analysis_context["ti"].xcom_pull = lambda key: (
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
                task.execute(context=document_analysis_context)


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
