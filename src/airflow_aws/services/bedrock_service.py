"""Bedrock service layer for Claude API interactions."""

import json
import logging
from typing import Any, Dict, Iterator, List, Optional

import boto3
from anthropic import AnthropicBedrock

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class BedrockServiceError(Exception):
    """Base exception for Bedrock service errors."""

    pass


class BedrockService:
    """Service for interacting with AWS Bedrock and Claude."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        role_arn: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """
        Initialize Bedrock service.

        Args:
            region_name: AWS region for Bedrock
            role_arn: Optional IAM role to assume
            model_id: Claude model ID to use
        """
        self.settings = get_settings()
        self.region = region_name or self.settings.aws.bedrock_region
        self.model_id = model_id or self.settings.aws.bedrock_model_id

        # Initialize boto3 client
        if role_arn:
            self.client = self._get_client_with_role(role_arn)
        else:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)

        # Initialize Anthropic Bedrock client
        self.anthropic_client = AnthropicBedrock(
            aws_region=self.region,
        )

        logger.info(
            f"BedrockService initialized with model: {self.model_id}, region: {self.region}"
        )

    def _get_client_with_role(self, role_arn: str):
        """
        Get boto3 client with assumed role.

        Args:
            role_arn: IAM role ARN to assume

        Returns:
            boto3 client with assumed role credentials
        """
        sts_client = boto3.client("sts")
        assumed_role = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="airflow-bedrock-session"
        )

        credentials = assumed_role["Credentials"]
        return boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    def invoke_claude(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Claude model via Bedrock.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system: Optional system prompt
            model_id: Optional override for model ID

        Returns:
            Dict with 'content', 'stop_reason', and 'usage' keys

        Raises:
            BedrockServiceError: If invocation fails
        """
        model = model_id or self.model_id

        try:
            logger.info(f"Invoking Claude model {model} with {len(messages)} messages")

            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
            )

            result = {
                "content": response.content[0].text,
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

            logger.info(f"Claude response received: {result['usage']} tokens used")
            return result

        except Exception as e:
            logger.error(f"Failed to invoke Claude: {e}")
            raise BedrockServiceError(f"Failed to invoke Claude: {e}") from e

    def invoke_claude_streaming(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Invoke Claude model with streaming response.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            model_id: Optional override for model ID

        Yields:
            Streaming response text chunks

        Raises:
            BedrockServiceError: If invocation fails
        """
        model = model_id or self.model_id

        try:
            logger.info(f"Invoking Claude model {model} with streaming")

            with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Failed to invoke Claude with streaming: {e}")
            raise BedrockServiceError(f"Failed to invoke Claude with streaming: {e}") from e

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

        Raises:
            BedrockServiceError: If chat fails
        """
        messages = [{"role": "user", "content": user_message}]

        result = self.invoke_claude(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )

        return result["content"]

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

        Raises:
            BedrockServiceError: If analysis fails
        """
        system_prompt = "You are a document analysis assistant. Provide clear, structured analysis."

        messages = [
            {
                "role": "user",
                "content": f"{analysis_prompt}\n\nDocument:\n{document_text}",
            }
        ]

        return self.invoke_claude(
            messages=messages,
            max_tokens=max_tokens,
            system=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent analysis
        )

    def batch_process_documents(
        self,
        documents: List[str],
        processing_prompt: str,
        max_tokens: int = 2048,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch.

        Args:
            documents: List of document texts
            processing_prompt: Instructions for processing each document
            max_tokens: Maximum tokens per document

        Returns:
            List of processing results

        Raises:
            BedrockServiceError: If batch processing fails
        """
        results = []

        for i, doc in enumerate(documents):
            logger.info(f"Processing document {i + 1}/{len(documents)}")

            try:
                result = self.analyze_document(
                    document_text=doc,
                    analysis_prompt=processing_prompt,
                    max_tokens=max_tokens,
                )
                results.append(
                    {
                        "document_index": i,
                        "content": result["content"],
                        "usage": result["usage"],
                        "success": True,
                    }
                )
            except BedrockServiceError as e:
                logger.error(f"Failed to process document {i}: {e}")
                results.append(
                    {
                        "document_index": i,
                        "error": str(e),
                        "success": False,
                    }
                )

        logger.info(
            f"Batch processing complete: {sum(1 for r in results if r['success'])}/{len(documents)} successful"
        )
        return results
