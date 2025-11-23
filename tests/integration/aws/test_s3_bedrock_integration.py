"""
Integration tests for S3 + Bedrock workflows.

These tests demonstrate:
1. Integration between multiple AWS services
2. Real workflow scenarios (read from S3, process with AI, write back)
3. End-to-end data pipeline testing
4. Error handling across service boundaries
"""

import json
from io import BytesIO

import pytest
from src.airflow_demo.services.bedrock_service import BedrockService
from src.airflow_demo.services.s3_service import S3Service

from tests.utils.test_helpers import BedrockTestHelper


@pytest.mark.integration
@pytest.mark.aws
class TestS3BedrockDocumentAnalysisWorkflow:
    """Test complete workflow: S3 -> Bedrock -> S3."""

    def test_analyze_document_from_s3(self, s3_client, bedrock_client, s3_bucket, bedrock_model_id):
        """
        Test complete workflow:
        1. Upload document to S3
        2. Read document from S3
        3. Analyze with Bedrock
        4. Write results back to S3
        """
        # Setup services
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Step 1: Upload document to S3
        document_text = """
        Artificial Intelligence and Machine Learning are transforming
        how businesses operate. Companies are using AI for automation,
        prediction, and decision-making across various industries.
        """

        s3_service.write_json(
            {"content": document_text, "type": "article"},
            s3_bucket,
            "input/document.json",
        )

        # Step 2: Read document from S3
        document_data = s3_service.read_json(s3_bucket, "input/document.json")
        assert document_data["content"] == document_text

        # Step 3: Mock Bedrock analysis
        analysis_result = "This document discusses AI and ML transformation in business."
        response_data = BedrockTestHelper.create_invoke_response(analysis_result)
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        analysis = bedrock_service.analyze_document(
            document_data["content"],
            "Summarize this document in one sentence.",
        )

        # Step 4: Write results back to S3
        result_data = {
            "original_key": "input/document.json",
            "analysis": analysis,
            "model": bedrock_model_id,
        }

        s3_service.write_json(result_data, s3_bucket, "output/analysis.json", indent=2)

        # Verify results
        saved_result = s3_service.read_json(s3_bucket, "output/analysis.json")
        assert saved_result["analysis"] == analysis_result
        assert saved_result["original_key"] == "input/document.json"

    def test_batch_document_analysis(self, s3_client, bedrock_client, s3_bucket, bedrock_model_id):
        """
        Test batch processing of multiple documents:
        1. Upload multiple documents to S3
        2. Process each with Bedrock
        3. Write all results to S3
        """
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload multiple documents
        documents = [
            {"id": 1, "text": "Document 1 about AI"},
            {"id": 2, "text": "Document 2 about ML"},
            {"id": 3, "text": "Document 3 about Data Science"},
        ]

        for doc in documents:
            s3_service.write_json(doc, s3_bucket, f"batch/input/doc_{doc['id']}.json")

        # List all documents
        objects = s3_service.list_objects(s3_bucket, prefix="batch/input/")
        assert len(objects) == 3

        # Process each document
        results = []
        for obj in objects:
            # Read document
            doc_data = s3_service.read_json(s3_bucket, obj["Key"])

            # Mock Bedrock response
            analysis = f"Analysis of document {doc_data['id']}"
            response_data = BedrockTestHelper.create_invoke_response(analysis)
            bedrock_client.invoke_model.return_value = {
                "body": BytesIO(response_data["body"]),
                "ResponseMetadata": response_data["ResponseMetadata"],
            }

            # Analyze
            result = bedrock_service.chat(f"Analyze this: {doc_data['text']}", max_tokens=100)

            results.append({"doc_id": doc_data["id"], "analysis": result})

        # Write batch results
        s3_service.write_json({"results": results}, s3_bucket, "batch/output/all_results.json")

        # Verify
        saved_results = s3_service.read_json(s3_bucket, "batch/output/all_results.json")
        assert len(saved_results["results"]) == 3

    def test_streaming_analysis_to_s3(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id, temp_dir
    ):
        """
        Test streaming Bedrock response and saving to S3:
        1. Read document from S3
        2. Stream analysis from Bedrock
        3. Collect chunks and save to S3
        """
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload source document
        s3_service.write_json({"text": "Source document"}, s3_bucket, "streaming/input.json")

        # Mock streaming response
        full_response = "This is a streaming analysis of the document."
        chunks = BedrockTestHelper.create_streaming_chunks(full_response, chunk_size=10)
        bedrock_client.invoke_model_with_response_stream.return_value = {"body": chunks}

        # Stream and collect
        collected_chunks = []
        for chunk in bedrock_service.chat_streaming("Analyze document"):
            collected_chunks.append(chunk)

        full_text = "".join(collected_chunks)

        # Save to S3
        s3_service.write_json({"streaming_result": full_text}, s3_bucket, "streaming/output.json")

        # Verify
        result = s3_service.read_json(s3_bucket, "streaming/output.json")
        assert full_response in result["streaming_result"]


@pytest.mark.integration
@pytest.mark.aws
class TestS3BedrockErrorHandling:
    """Test error handling across S3 and Bedrock integration."""

    def test_handle_missing_s3_document(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id
    ):
        """Test graceful handling when S3 document is missing."""
        from src.airflow_demo.services.s3_service import S3ObjectNotFoundError

        s3_service = S3Service()
        s3_service.client = s3_client

        with pytest.raises(S3ObjectNotFoundError):
            s3_service.read_json(s3_bucket, "missing/document.json")

    def test_handle_bedrock_error_and_log_to_s3(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id
    ):
        """Test handling Bedrock errors and logging to S3."""
        from botocore.exceptions import ClientError
        from src.airflow_demo.services.bedrock_service import BedrockServiceError

        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload document
        s3_service.write_json({"text": "Test document"}, s3_bucket, "test/input.json")

        # Mock Bedrock error
        bedrock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )

        # Try to process and catch error
        error_log = {"status": "error", "message": ""}

        try:
            messages = [{"role": "user", "content": [{"type": "text", "text": "Test"}]}]
            bedrock_service.invoke(messages=messages)
        except BedrockServiceError as e:
            error_log["message"] = str(e)
            error_log["error_type"] = "BedrockServiceError"

        # Log error to S3
        s3_service.write_json(error_log, s3_bucket, "test/error.json")

        # Verify error was logged
        saved_error = s3_service.read_json(s3_bucket, "test/error.json")
        assert saved_error["status"] == "error"
        assert (
            "ThrottlingException" in saved_error["message"]
            or "Rate exceeded" in saved_error["message"]
        )

    def test_partial_batch_failure_handling(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id
    ):
        """Test handling partial failures in batch processing."""
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload documents
        for i in range(3):
            s3_service.write_json(
                {"id": i, "text": f"Document {i}"}, s3_bucket, f"batch/doc_{i}.json"
            )

        # Process with some failures
        results = {"successful": [], "failed": []}

        for i in range(3):
            try:
                doc = s3_service.read_json(s3_bucket, f"batch/doc_{i}.json")

                # Simulate failure on document 1
                if i == 1:
                    from botocore.exceptions import ClientError

                    bedrock_client.invoke_model.side_effect = ClientError(
                        {"Error": {"Code": "ValidationException", "Message": "Invalid"}},
                        "InvokeModel",
                    )
                else:
                    response_data = BedrockTestHelper.create_invoke_response(f"Result {i}")
                    bedrock_client.invoke_model.return_value = {
                        "body": BytesIO(response_data["body"]),
                        "ResponseMetadata": response_data["ResponseMetadata"],
                    }
                    bedrock_client.invoke_model.side_effect = None

                result = bedrock_service.chat(doc["text"])
                results["successful"].append({"id": i, "result": result})

            except Exception as e:
                results["failed"].append({"id": i, "error": str(e)})

        # Save results
        s3_service.write_json(results, s3_bucket, "batch/results.json")

        # Verify
        saved_results = s3_service.read_json(s3_bucket, "batch/results.json")
        assert len(saved_results["successful"]) == 2  # 0 and 2
        assert len(saved_results["failed"]) == 1  # 1


@pytest.mark.integration
@pytest.mark.aws
class TestS3BedrockDataTransformation:
    """Test data transformation workflows using S3 and Bedrock."""

    def test_transform_json_with_ai(self, s3_client, bedrock_client, s3_bucket, bedrock_model_id):
        """
        Test AI-powered data transformation:
        1. Read structured data from S3
        2. Transform using Bedrock
        3. Write transformed data back to S3
        """
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload source data
        source_data = {
            "records": [
                {"name": "John Doe", "occupation": "Engineer"},
                {"name": "Jane Smith", "occupation": "Doctor"},
            ]
        }
        s3_service.write_json(source_data, s3_bucket, "transform/input.json")

        # Read and transform
        data = s3_service.read_json(s3_bucket, "transform/input.json")

        # Mock transformation result
        transformed_json = json.dumps(
            {
                "people": [
                    {"fullName": "John Doe", "profession": "Engineer"},
                    {"fullName": "Jane Smith", "profession": "Doctor"},
                ]
            }
        )

        response_data = BedrockTestHelper.create_invoke_response(transformed_json)
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        prompt = f"Transform this JSON by renaming 'name' to 'fullName' and 'occupation' to 'profession': {json.dumps(data)}"
        result_text = bedrock_service.chat(prompt, temperature=0.0)

        # Parse and save transformed data
        # In real scenario, you'd extract JSON from the response
        s3_service.write_json({"transformed": result_text}, s3_bucket, "transform/output.json")

        # Verify
        output = s3_service.read_json(s3_bucket, "transform/output.json")
        assert "transformed" in output

    def test_enrich_data_with_ai_insights(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id
    ):
        """
        Test enriching data with AI insights:
        1. Read data from S3
        2. Generate insights using Bedrock
        3. Merge insights with original data
        4. Save enriched data to S3
        """
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload data
        data = {
            "product": "Smart Watch",
            "reviews": [
                "Great battery life!",
                "Screen is too small",
                "Love the fitness tracking",
            ],
        }
        s3_service.write_json(data, s3_bucket, "enrich/product.json")

        # Read data
        product_data = s3_service.read_json(s3_bucket, "enrich/product.json")

        # Generate insight
        insight = "Overall positive sentiment with focus on battery and fitness features. Concern about screen size."
        response_data = BedrockTestHelper.create_invoke_response(insight)
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        prompt = f"Analyze sentiment of these reviews: {product_data['reviews']}"
        ai_insight = bedrock_service.chat(prompt)

        # Enrich data
        enriched_data = {
            **product_data,
            "ai_insights": {
                "sentiment_analysis": ai_insight,
                "model": bedrock_model_id,
            },
        }

        # Save enriched data
        s3_service.write_json(enriched_data, s3_bucket, "enrich/product_enriched.json")

        # Verify
        saved_data = s3_service.read_json(s3_bucket, "enrich/product_enriched.json")
        assert "ai_insights" in saved_data
        assert "sentiment_analysis" in saved_data["ai_insights"]
        assert saved_data["product"] == "Smart Watch"


@pytest.mark.integration
@pytest.mark.aws
@pytest.mark.slow
class TestS3BedrockPerformance:
    """Performance tests for S3 + Bedrock integration."""

    def test_concurrent_document_processing(
        self, s3_client, bedrock_client, s3_bucket, bedrock_model_id, performance_timer
    ):
        """Test processing multiple documents with performance tracking."""
        s3_service = S3Service()
        s3_service.client = s3_client

        bedrock_service = BedrockService(model_id=bedrock_model_id)
        bedrock_service.client = bedrock_client

        # Upload multiple documents
        num_docs = 5
        for i in range(num_docs):
            s3_service.write_json(
                {"id": i, "text": f"Document {i} content"}, s3_bucket, f"perf/doc_{i}.json"
            )

        # Mock response
        response_data = BedrockTestHelper.create_invoke_response("Analysis result")
        bedrock_client.invoke_model.return_value = {
            "body": BytesIO(response_data["body"]),
            "ResponseMetadata": response_data["ResponseMetadata"],
        }

        # Process all documents
        with performance_timer as timer:
            for i in range(num_docs):
                doc = s3_service.read_json(s3_bucket, f"perf/doc_{i}.json")
                result = bedrock_service.chat(doc["text"])
                s3_service.write_json({"result": result}, s3_bucket, f"perf/result_{i}.json")

        # Performance assertion
        assert timer.elapsed < 5.0  # Should be fast with mocked services
        print(f"Processed {num_docs} documents in {timer.elapsed:.2f} seconds")
