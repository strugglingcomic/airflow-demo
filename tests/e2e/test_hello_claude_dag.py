"""
E2E test for hello_claude DAG.

This test demonstrates real end-to-end execution of a DAG task that invokes
Claude via Bedrock, with proper mocking of the AWS Bedrock API.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from airflow.models import DagBag

from tests.utils.test_helpers import BedrockTestHelper


@pytest.fixture
def dag_bag(airflow_db):
    """Load the DAG bag with test DAGs."""
    dags_folder = Path(__file__).parent.parent / "fixtures" / "dags"
    return DagBag(dag_folder=str(dags_folder), include_examples=False)


@pytest.fixture
def hello_claude_dag(dag_bag):
    """Get the hello_claude DAG."""
    dag = dag_bag.get_dag("hello_claude")
    assert dag is not None, "hello_claude DAG not found in DagBag"
    return dag


@pytest.mark.e2e
@pytest.mark.bedrock
class TestHelloClaudeDAG:
    """E2E tests for hello_claude DAG."""

    def test_dag_loaded(self, hello_claude_dag):
        """Test that DAG is properly loaded."""
        assert hello_claude_dag is not None
        assert hello_claude_dag.dag_id == "hello_claude"

    def test_dag_structure(self, hello_claude_dag):
        """Test DAG has correct structure."""
        assert len(hello_claude_dag.tasks) == 1
        assert hello_claude_dag.has_task("say_hello")

        task = hello_claude_dag.get_task("say_hello")
        assert task.task_id == "say_hello"

    def test_say_hello_task_execution(
        self,
        hello_claude_dag,
        bedrock_client,
    ):
        """Test the say_hello task executes successfully with mocked Bedrock."""
        # Mock Bedrock response
        claude_response = "Hello! I'm Claude, an AI assistant created by Anthropic."
        response_data = BedrockTestHelper.create_invoke_response(
            claude_response, input_tokens=15, output_tokens=20
        )
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        # Get the task's Python callable
        task = hello_claude_dag.get_task("say_hello")
        python_callable = task.python_callable

        # Patch BedrockService to use our mocked client
        with patch("src.airflow_demo.services.bedrock_service.boto3.client") as mock_boto:
            mock_boto.return_value = bedrock_client

            # Execute the Python callable directly (no full Airflow context needed)
            result = python_callable()

            # Verify the result
            assert result is not None
            assert "Claude" in result or "Anthropic" in result or "assistant" in result
            print(f"Task execution result: {result}")

            # Verify Bedrock was called
            bedrock_client.invoke_model.assert_called_once()

    def test_say_hello_task_with_error_handling(
        self,
        hello_claude_dag,
        bedrock_client,
    ):
        """Test that task handles Bedrock errors appropriately."""
        from botocore.exceptions import ClientError
        from src.airflow_demo.services.bedrock_service import BedrockServiceError

        # Mock a Bedrock error
        error = ClientError(
            {
                "Error": {
                    "Code": "ThrottlingException",
                    "Message": "Rate exceeded",
                }
            },
            "InvokeModel",
        )
        bedrock_client.invoke_model.side_effect = error

        # Get the task's Python callable
        task = hello_claude_dag.get_task("say_hello")
        python_callable = task.python_callable

        # Patch BedrockService to use our mocked client
        with patch("src.airflow_demo.services.bedrock_service.boto3.client") as mock_boto:
            mock_boto.return_value = bedrock_client

            # Execute should raise BedrockServiceError
            with pytest.raises(BedrockServiceError, match="Invocation failed"):
                python_callable()

    def test_dag_bag_has_no_import_errors(self, dag_bag):
        """Test that DAG bag has no import errors."""
        assert not dag_bag.import_errors, f"Import errors: {dag_bag.import_errors}"

    def test_dag_tags(self, hello_claude_dag):
        """Test DAG has expected tags."""
        assert "bedrock" in hello_claude_dag.tags
        assert "claude" in hello_claude_dag.tags
        assert "hello-world" in hello_claude_dag.tags
