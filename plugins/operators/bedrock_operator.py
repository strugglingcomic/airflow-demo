"""Bedrock Operator for Claude invocations in Airflow."""

import logging
from typing import Any, Dict, List, Optional

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from plugins.hooks.bedrock_hook import BedrockHook

logger = logging.getLogger(__name__)


class BedrockClaudeOperator(BaseOperator):
    """
    Operator to invoke Claude via AWS Bedrock.

    This operator provides a simple interface for invoking Claude models
    within Airflow DAGs, with full support for templating and XCom.

    :param messages: List of message dictionaries with 'role' and 'content'
    :param max_tokens: Maximum tokens to generate (default: 4096)
    :param temperature: Sampling temperature 0.0-1.0 (default: 1.0)
    :param system: Optional system prompt
    :param aws_conn_id: AWS connection ID (default: aws_default)
    :param region_name: AWS region
    :param model_id: Override default Claude model ID
    :param output_key: XCom key to push response to (default: claude_response)
    :param return_full_response: If True, return full response dict; if False, return only content

    **Example**::

        invoke_claude = BedrockClaudeOperator(
            task_id='analyze_data',
            messages=[
                {
                    "role": "user",
                    "content": "Analyze this data: {{ ti.xcom_pull(task_ids='fetch_data') }}"
                }
            ],
            system="You are a data analysis expert.",
            temperature=0.7,
        )
    """

    template_fields = ("messages", "system", "max_tokens", "temperature")
    template_ext = (".json",)
    ui_color = "#FF9900"  # AWS orange
    ui_fgcolor = "#FFFFFF"

    @apply_defaults
    def __init__(
        self,
        *,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        aws_conn_id: str = "aws_default",
        region_name: Optional[str] = None,
        model_id: Optional[str] = None,
        output_key: str = "claude_response",
        return_full_response: bool = True,
        **kwargs,
    ):
        """
        Initialize Bedrock Claude operator.

        Args:
            messages: List of message dicts
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            system: System prompt
            aws_conn_id: AWS connection ID
            region_name: AWS region
            model_id: Claude model ID
            output_key: XCom output key
            return_full_response: Return full response or just content
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system = system
        self.aws_conn_id = aws_conn_id
        self.region_name = region_name
        self.model_id = model_id
        self.output_key = output_key
        self.return_full_response = return_full_response

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Claude invocation.

        Args:
            context: Airflow task context

        Returns:
            Claude response (full dict or just content, based on return_full_response)
        """
        hook = BedrockHook(
            aws_conn_id=self.aws_conn_id,
            region_name=self.region_name,
            model_id=self.model_id,
        )

        self.log.info(f"Invoking Claude with {len(self.messages)} messages")
        self.log.info(f"Temperature: {self.temperature}, Max tokens: {self.max_tokens}")

        response = hook.invoke_claude(
            messages=self.messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system,
        )

        # Log usage
        usage = response.get("usage", {})
        self.log.info(
            f"Claude response received. "
            f"Input tokens: {usage.get('input_tokens', 0)}, "
            f"Output tokens: {usage.get('output_tokens', 0)}"
        )

        # Push to XCom
        context["task_instance"].xcom_push(key=self.output_key, value=response)

        # Also push individual components for easy access
        context["task_instance"].xcom_push(
            key=f"{self.output_key}_content", value=response.get("content", "")
        )
        context["task_instance"].xcom_push(key=f"{self.output_key}_usage", value=usage)

        # Return based on configuration
        if self.return_full_response:
            return response
        else:
            return response.get("content", "")


class BedrockDocumentAnalysisOperator(BaseOperator):
    """
    Operator to analyze documents using Claude via Bedrock.

    This specialized operator is optimized for document analysis tasks,
    with built-in prompt templates and structured output.

    :param document_text: Text of the document to analyze (supports templating)
    :param analysis_prompt: Prompt describing what to analyze
    :param max_tokens: Maximum tokens for analysis (default: 4096)
    :param aws_conn_id: AWS connection ID
    :param output_key: XCom key for results

    **Example**::

        analyze_doc = BedrockDocumentAnalysisOperator(
            task_id='analyze_customer_feedback',
            document_text="{{ ti.xcom_pull(task_ids='fetch_feedback') }}",
            analysis_prompt="Summarize key themes and sentiment",
        )
    """

    template_fields = ("document_text", "analysis_prompt")
    ui_color = "#FF6B35"

    @apply_defaults
    def __init__(
        self,
        *,
        document_text: str,
        analysis_prompt: str,
        max_tokens: int = 4096,
        aws_conn_id: str = "aws_default",
        region_name: Optional[str] = None,
        output_key: str = "analysis_result",
        **kwargs,
    ):
        """
        Initialize document analysis operator.

        Args:
            document_text: Document to analyze
            analysis_prompt: Analysis instructions
            max_tokens: Max tokens
            aws_conn_id: AWS connection
            region_name: AWS region
            output_key: XCom output key
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.document_text = document_text
        self.analysis_prompt = analysis_prompt
        self.max_tokens = max_tokens
        self.aws_conn_id = aws_conn_id
        self.region_name = region_name
        self.output_key = output_key

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute document analysis.

        Args:
            context: Airflow task context

        Returns:
            Analysis results
        """
        hook = BedrockHook(
            aws_conn_id=self.aws_conn_id,
            region_name=self.region_name,
        )

        self.log.info(f"Analyzing document of length: {len(self.document_text)}")

        response = hook.analyze_document(
            document_text=self.document_text,
            analysis_prompt=self.analysis_prompt,
            max_tokens=self.max_tokens,
        )

        # Log results
        self.log.info(
            f"Analysis complete. Output length: {len(response.get('content', ''))}"
        )

        # Push to XCom
        context["task_instance"].xcom_push(key=self.output_key, value=response)

        return response
