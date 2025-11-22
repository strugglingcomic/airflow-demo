"""
Bedrock Service for handling AWS Bedrock AI operations in Airflow.

This module provides a high-level interface for Bedrock operations
with support for Claude models, streaming, and error handling.
"""

import json
import logging
from typing import Any, Dict, Iterator, Optional

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class BedrockServiceError(Exception):
    """Base exception for BedrockService errors."""

    pass


class BedrockModelError(BedrockServiceError):
    """Exception raised when there's a model-specific error."""

    pass


class BedrockService:
    """Service class for AWS Bedrock operations."""

    # Claude model IDs
    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"

    def __init__(
        self,
        model_id: str = CLAUDE_3_5_SONNET,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        """
        Initialize Bedrock service.

        Args:
            model_id: Bedrock model ID to use
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
        """
        self.model_id = model_id
        self.region_name = region_name
        self.client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        logger.info(f"BedrockService initialized with model: {model_id}")

    def invoke(
        self,
        messages: list[Dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system: Optional[str] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock model (non-streaming).

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            top_p: Top-p sampling parameter
            system: Optional system prompt
            stop_sequences: Optional stop sequences

        Returns:
            Response from Bedrock model

        Raises:
            BedrockServiceError: If invocation fails
        """
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
            }

            if system:
                payload["system"] = system
            if stop_sequences:
                payload["stop_sequences"] = stop_sequences

            response = self.client.invoke_model(
                modelId=self.model_id, body=json.dumps(payload)
            )

            response_body = json.loads(response["body"].read())
            logger.info(
                f"Invoked Bedrock model: {self.model_id}, "
                f"tokens: {response_body.get('usage', {})}"
            )
            return response_body

        except ClientError as e:
            logger.error(f"Failed to invoke Bedrock model: {e}")
            raise BedrockServiceError(f"Invocation failed: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Bedrock response: {e}")
            raise BedrockServiceError(f"Response parsing failed: {e}") from e

    def invoke_streaming(
        self,
        messages: list[Dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system: Optional[str] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> Iterator[str]:
        """
        Invoke Bedrock model with streaming.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            top_p: Top-p sampling parameter
            system: Optional system prompt
            stop_sequences: Optional stop sequences

        Yields:
            Text chunks from the streaming response

        Raises:
            BedrockServiceError: If invocation fails
        """
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
            }

            if system:
                payload["system"] = system
            if stop_sequences:
                payload["stop_sequences"] = stop_sequences

            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id, body=json.dumps(payload)
            )

            for event in response["body"]:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]["delta"]
                    if "text" in delta:
                        yield delta["text"]

            logger.info(f"Completed streaming invocation of {self.model_id}")

        except ClientError as e:
            logger.error(f"Failed to invoke Bedrock model with streaming: {e}")
            raise BedrockServiceError(f"Streaming invocation failed: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Bedrock streaming response: {e}")
            raise BedrockServiceError(f"Streaming response parsing failed: {e}") from e

    def chat(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> str:
        """
        Simple chat interface - send a prompt and get a response.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            system: Optional system prompt

        Returns:
            Response text from the model

        Raises:
            BedrockServiceError: If chat fails
        """
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

        response = self.invoke(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

        return self._extract_text_from_response(response)

    def chat_streaming(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Simple streaming chat interface.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            system: Optional system prompt

        Yields:
            Text chunks from the streaming response

        Raises:
            BedrockServiceError: If chat fails
        """
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

        yield from self.invoke_streaming(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

    def analyze_document(
        self,
        document_text: str,
        analysis_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.5,
    ) -> str:
        """
        Analyze a document using Claude.

        Args:
            document_text: Text of the document to analyze
            analysis_prompt: Instructions for analysis
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Analysis result

        Raises:
            BedrockServiceError: If analysis fails
        """
        system_prompt = "You are an expert document analyzer."

        combined_prompt = f"""Document to analyze:
<document>
{document_text}
</document>

Analysis instructions:
{analysis_prompt}
"""

        return self.chat(
            prompt=combined_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
        )

    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from Bedrock response.

        Args:
            response: Bedrock API response

        Returns:
            Extracted text

        Raises:
            BedrockServiceError: If extraction fails
        """
        try:
            if "content" not in response:
                raise BedrockServiceError("Failed to extract text: missing 'content' field")

            content_blocks = response.get("content", [])
            # Empty content is valid and returns empty string
            if not content_blocks:
                return ""

            text_blocks = [
                block["text"] for block in content_blocks if block.get("type") == "text"
            ]
            return " ".join(text_blocks)
        except (KeyError, TypeError) as e:
            raise BedrockServiceError(f"Failed to extract text from response: {e}") from e

    def get_usage_stats(self, response: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract usage statistics from response.

        Args:
            response: Bedrock API response

        Returns:
            Dictionary with input_tokens and output_tokens

        Raises:
            BedrockServiceError: If extraction fails
        """
        try:
            usage = response.get("usage", {})
            return {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }
        except (KeyError, TypeError) as e:
            raise BedrockServiceError(f"Failed to extract usage stats: {e}") from e
