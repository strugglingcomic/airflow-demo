"""Bedrock Hook for Airflow integration."""

import logging
from typing import Any, Dict, Iterator, List, Optional

from airflow.hooks.base import BaseHook

from src.airflow_aws.services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)


class BedrockHook(BaseHook):
    """
    Hook for AWS Bedrock operations with Claude models.

    This hook provides integration between Airflow and AWS Bedrock,
    specifically optimized for Claude model invocations.

    :param aws_conn_id: AWS connection ID (default: aws_default)
    :param region_name: AWS region for Bedrock
    :param role_arn: Optional IAM role to assume
    :param model_id: Claude model ID to use
    """

    conn_name_attr = "aws_conn_id"
    default_conn_name = "aws_default"
    conn_type = "aws"
    hook_name = "AWS Bedrock"

    def __init__(
        self,
        aws_conn_id: str = "aws_default",
        region_name: Optional[str] = None,
        role_arn: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """
        Initialize Bedrock hook.

        Args:
            aws_conn_id: Airflow AWS connection ID
            region_name: AWS region
            role_arn: Optional IAM role ARN to assume
            model_id: Claude model ID
        """
        super().__init__()
        self.aws_conn_id = aws_conn_id
        self.region_name = region_name
        self.role_arn = role_arn
        self.model_id = model_id
        self._service: Optional[BedrockService] = None

        logger.info(f"BedrockHook initialized with connection: {aws_conn_id}")

    def get_conn(self) -> BedrockService:
        """
        Get Bedrock service instance.

        Returns:
            BedrockService instance
        """
        if self._service is None:
            self._service = BedrockService(
                region_name=self.region_name,
                role_arn=self.role_arn,
                model_id=self.model_id,
            )
            logger.info("BedrockService connection established")
        return self._service

    def invoke_claude(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Claude model via Bedrock.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system: Optional system prompt

        Returns:
            Dict containing Claude's response

        Example:
            >>> hook = BedrockHook()
            >>> messages = [{"role": "user", "content": "Hello Claude!"}]
            >>> response = hook.invoke_claude(messages)
            >>> print(response['content'])
        """
        service = self.get_conn()
        logger.info(f"Invoking Claude with {len(messages)} messages")

        response = service.invoke_claude(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

        logger.info(
            f"Claude invocation complete. "
            f"Input tokens: {response['usage']['input_tokens']}, "
            f"Output tokens: {response['usage']['output_tokens']}"
        )

        return response

    def invoke_claude_streaming(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Invoke Claude model with streaming response.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt

        Yields:
            Text chunks from streaming response
        """
        service = self.get_conn()
        logger.info(f"Invoking Claude with streaming for {len(messages)} messages")

        yield from service.invoke_claude_streaming(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

    def chat(
        self,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> str:
        """
        Simple chat interface for single message interaction.

        Args:
            user_message: User's message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt

        Returns:
            Claude's response text
        """
        service = self.get_conn()
        return service.chat(
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

    def analyze_document(
        self,
        document_text: str,
        analysis_prompt: str,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Analyze a document using Claude.

        Args:
            document_text: The document text to analyze
            analysis_prompt: Instructions for what to analyze
            max_tokens: Maximum tokens for response

        Returns:
            Dict with analysis results
        """
        service = self.get_conn()
        logger.info(f"Analyzing document of length {len(document_text)}")

        return service.analyze_document(
            document_text=document_text,
            analysis_prompt=analysis_prompt,
            max_tokens=max_tokens,
        )

    def test_connection(self) -> tuple[bool, str]:
        """
        Test the Bedrock connection.

        Returns:
            Tuple of (success, message)
        """
        try:
            service = self.get_conn()
            # Simple test invocation
            response = service.chat("Hello", max_tokens=10)
            return True, f"Connection successful. Response: {response[:50]}..."
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"
