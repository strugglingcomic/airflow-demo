"""
Unit tests for BedrockService.

These tests demonstrate TDD for AI/ML service integration:
1. Mocking AI model responses
2. Testing streaming vs non-streaming
3. Testing error handling for AI services
4. Testing token usage tracking
"""

import json
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from src.airflow_demo.services.bedrock_service import (
    BedrockService,
    BedrockServiceError,
)

from tests.utils.test_helpers import BedrockTestHelper


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceInitialization:
    """Test BedrockService initialization."""

    def test_init_with_default_model(self):
        """Test initialization with default Claude model."""
        service = BedrockService()
        assert service.model_id == BedrockService.CLAUDE_3_5_SONNET
        assert service.region_name == "us-east-1"
        assert service.client is not None

    def test_init_with_custom_model(self):
        """Test initialization with custom model ID."""
        service = BedrockService(model_id=BedrockService.CLAUDE_3_HAIKU)
        assert service.model_id == BedrockService.CLAUDE_3_HAIKU

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        service = BedrockService(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="us-west-2",
        )
        assert service.region_name == "us-west-2"

    def test_model_constants_defined(self):
        """Test that model ID constants are properly defined."""
        assert hasattr(BedrockService, "CLAUDE_3_5_SONNET")
        assert hasattr(BedrockService, "CLAUDE_3_OPUS")
        assert hasattr(BedrockService, "CLAUDE_3_HAIKU")
        assert "anthropic.claude" in BedrockService.CLAUDE_3_5_SONNET


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceInvoke:
    """Test BedrockService.invoke method."""

    def test_invoke_success(self, bedrock_client, bedrock_model_id):
        """Test successful model invocation."""
        service = BedrockService(model_id=bedrock_model_id)

        # Mock the response
        response_data = BedrockTestHelper.create_invoke_response("Hello from Claude!")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }
        service.client = bedrock_client

        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]

        result = service.invoke(messages=messages)

        assert "content" in result
        assert result["content"][0]["text"] == "Hello from Claude!"
        assert "usage" in result

        # Verify correct API call
        bedrock_client.invoke_model.assert_called_once()
        call_args = bedrock_client.invoke_model.call_args
        assert call_args[1]["modelId"] == bedrock_model_id

    def test_invoke_with_system_prompt(self, bedrock_client, bedrock_model_id):
        """Test invocation with system prompt."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [{"role": "user", "content": [{"type": "text", "text": "Question"}]}]
        system_prompt = "You are a helpful assistant."

        service.invoke(messages=messages, system=system_prompt)

        # Verify system prompt was included in request
        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        assert body["system"] == system_prompt

    def test_invoke_with_custom_parameters(self, bedrock_client, bedrock_model_id):
        """Test invocation with custom temperature and max_tokens."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]

        service.invoke(
            messages=messages,
            max_tokens=2048,
            temperature=0.5,
            top_p=0.95,
        )

        # Verify parameters
        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        assert body["max_tokens"] == 2048
        assert body["temperature"] == 0.5
        assert body["top_p"] == 0.95

    def test_invoke_with_stop_sequences(self, bedrock_client, bedrock_model_id):
        """Test invocation with stop sequences."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]
        stop_sequences = ["END", "STOP"]

        service.invoke(messages=messages, stop_sequences=stop_sequences)

        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        assert body["stop_sequences"] == stop_sequences

    def test_invoke_client_error(self, bedrock_client, bedrock_model_id):
        """Test handling of client errors during invocation."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        bedrock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            "InvokeModel",
        )

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]

        with pytest.raises(BedrockServiceError, match="Invocation failed"):
            service.invoke(messages=messages)


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceStreaming:
    """Test BedrockService.invoke_streaming method."""

    def test_invoke_streaming_success(self, bedrock_client, bedrock_model_id):
        """Test successful streaming invocation."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        # Create streaming response
        chunks = BedrockTestHelper.create_streaming_chunks("Hello from Claude!", chunk_size=5)
        bedrock_client.invoke_model_with_response_stream.return_value = {"body": chunks}

        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]

        result_chunks = list(service.invoke_streaming(messages=messages))

        # Verify we got text chunks
        assert len(result_chunks) > 0
        full_text = "".join(result_chunks)
        assert "Hello from Claude!" in full_text

    def test_invoke_streaming_with_system_prompt(self, bedrock_client, bedrock_model_id):
        """Test streaming with system prompt."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        chunks = BedrockTestHelper.create_streaming_chunks("Response")
        bedrock_client.invoke_model_with_response_stream.return_value = {"body": chunks}

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]
        system_prompt = "You are helpful."

        list(service.invoke_streaming(messages=messages, system=system_prompt))

        # Verify system prompt in request
        call_args = bedrock_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args[1]["body"])
        assert body["system"] == system_prompt

    def test_invoke_streaming_client_error(self, bedrock_client, bedrock_model_id):
        """Test error handling in streaming."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        bedrock_client.invoke_model_with_response_stream.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModelWithResponseStream",
        )

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]

        with pytest.raises(BedrockServiceError, match="Streaming invocation failed"):
            list(service.invoke_streaming(messages=messages))


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceChat:
    """Test BedrockService.chat convenience method."""

    def test_chat_success(self, bedrock_client, bedrock_model_id):
        """Test simple chat interface."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("I'm doing well, thank you!")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        result = service.chat("How are you?")

        assert isinstance(result, str)
        assert "doing well" in result.lower()

    def test_chat_with_system_prompt(self, bedrock_client, bedrock_model_id):
        """Test chat with system prompt."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Bonjour!")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        result = service.chat(
            "Say hello",
            system="You always respond in French.",
        )

        assert isinstance(result, str)

    def test_chat_streaming_success(self, bedrock_client, bedrock_model_id):
        """Test streaming chat interface."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        chunks = BedrockTestHelper.create_streaming_chunks("Streaming response!")
        bedrock_client.invoke_model_with_response_stream.return_value = {"body": chunks}

        result_chunks = list(service.chat_streaming("Test prompt"))

        assert len(result_chunks) > 0
        full_text = "".join(result_chunks)
        assert "Streaming response!" in full_text


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceAnalyzeDocument:
    """Test BedrockService.analyze_document method."""

    def test_analyze_document_success(self, bedrock_client, bedrock_model_id):
        """Test document analysis."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response(
            "This document is about AI technology."
        )
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        document = "Artificial Intelligence is transforming industries..."
        analysis_prompt = "Summarize the main topic of this document."

        result = service.analyze_document(document, analysis_prompt)

        assert isinstance(result, str)
        assert len(result) > 0

        # Verify the request included both document and instructions
        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        message_text = body["messages"][0]["content"][0]["text"]
        assert "Document to analyze" in message_text
        assert document in message_text
        assert analysis_prompt in message_text

    def test_analyze_document_with_custom_params(self, bedrock_client, bedrock_model_id):
        """Test document analysis with custom parameters."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Analysis result")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        service.analyze_document(
            "Document text",
            "Analyze this",
            max_tokens=3000,
            temperature=0.3,
        )

        # Verify custom parameters
        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        assert body["max_tokens"] == 3000
        assert body["temperature"] == 0.3


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceUtilities:
    """Test utility methods in BedrockService."""

    def test_extract_text_from_response(self):
        """Test text extraction from response."""
        service = BedrockService()

        response = {
            "content": [
                {"type": "text", "text": "First part. "},
                {"type": "text", "text": "Second part."},
            ]
        }

        result = service._extract_text_from_response(response)

        assert result == "First part.  Second part."

    def test_extract_text_empty_content(self):
        """Test text extraction with empty content."""
        service = BedrockService()

        response = {"content": []}

        result = service._extract_text_from_response(response)

        assert result == ""

    def test_extract_text_invalid_response(self):
        """Test text extraction with invalid response."""
        service = BedrockService()

        with pytest.raises(BedrockServiceError, match="Failed to extract text"):
            service._extract_text_from_response({})

    def test_get_usage_stats(self):
        """Test usage statistics extraction."""
        service = BedrockService()

        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 250,
            }
        }

        stats = service.get_usage_stats(response)

        assert stats["input_tokens"] == 100
        assert stats["output_tokens"] == 250

    def test_get_usage_stats_missing(self):
        """Test usage stats with missing data."""
        service = BedrockService()

        response = {}

        stats = service.get_usage_stats(response)

        assert stats["input_tokens"] == 0
        assert stats["output_tokens"] == 0


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceErrorHandling:
    """Test error handling in BedrockService."""

    def test_custom_exception_hierarchy(self):
        """Test custom exception hierarchy."""
        assert issubclass(BedrockServiceError, Exception)

    def test_error_messages_informative(self, bedrock_client):
        """Test that error messages are informative."""
        service = BedrockService()
        service.client = bedrock_client

        bedrock_client.invoke_model.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ModelTimeoutException",
                    "Message": "Model invocation timed out",
                }
            },
            "InvokeModel",
        )

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]

        try:
            service.invoke(messages=messages)
        except BedrockServiceError as e:
            assert "Invocation failed" in str(e)
            assert "ModelTimeoutException" in str(e) or "timed out" in str(e).lower()


@pytest.mark.unit
@pytest.mark.bedrock
class TestBedrockServiceMessageFormats:
    """Test different message formats and structures."""

    def test_single_turn_conversation(self, bedrock_client, bedrock_model_id):
        """Test single-turn conversation."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

        result = service.invoke(messages=messages)
        assert "content" in result

    def test_multi_turn_conversation(self, bedrock_client, bedrock_model_id):
        """Test multi-turn conversation."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [
            {"role": "user", "content": [{"type": "text", "text": "What's 2+2?"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "2+2 equals 4."}]},
            {"role": "user", "content": [{"type": "text", "text": "What about 3+3?"}]},
        ]

        result = service.invoke(messages=messages)
        assert "content" in result

        # Verify all messages were sent
        call_args = bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        assert len(body["messages"]) == 3


@pytest.mark.unit
@pytest.mark.bedrock
@pytest.mark.slow
class TestBedrockServicePerformance:
    """Performance and load tests for BedrockService."""

    def test_multiple_sequential_invocations(
        self, bedrock_client, bedrock_model_id, performance_timer
    ):
        """Test performance of multiple sequential invocations."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        response_data = BedrockTestHelper.create_invoke_response("Response")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]

        with performance_timer as timer:
            for _ in range(10):
                service.invoke(messages=messages)

        # Should be fast with mocked responses
        assert timer.elapsed < 1.0

    def test_token_usage_tracking(self, bedrock_client, bedrock_model_id, metrics_collector):
        """Test tracking token usage across multiple calls."""
        service = BedrockService(model_id=bedrock_model_id)
        service.client = bedrock_client

        for i in range(5):
            response_data = BedrockTestHelper.create_invoke_response(
                "Response",
                input_tokens=10 + i,
                output_tokens=20 + i * 2,
            )
            bedrock_client.invoke_model.return_value = {
                "body": BytesIO(response_data["body"]),
                "ResponseMetadata": response_data["ResponseMetadata"],
            }

            messages = [{"role": "user", "content": [{"type": "text", "text": f"Test {i}"}]}]
            result = service.invoke(messages=messages)

            stats = service.get_usage_stats(result)
            metrics_collector.record("input_tokens", stats["input_tokens"])
            metrics_collector.record("output_tokens", stats["output_tokens"])

        # Verify tracking
        assert len(metrics_collector.get("input_tokens")) == 5
        assert len(metrics_collector.get("output_tokens")) == 5
        assert sum(metrics_collector.get("input_tokens")) > 0
