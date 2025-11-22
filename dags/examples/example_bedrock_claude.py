"""
Example DAG demonstrating AWS Bedrock and Claude integration.

This DAG shows how to use the BedrockClaudeOperator to invoke Claude
for various tasks including simple chat, document analysis, and data processing.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.s3 import S3CreateObjectOperator

from plugins.operators.bedrock_operator import (
    BedrockClaudeOperator,
    BedrockDocumentAnalysisOperator,
)

# ====================
# DAG Configuration
# ====================

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ====================
# Helper Functions
# ====================


def process_claude_response(**context):
    """
    Process Claude's response from XCom.

    This function demonstrates how to retrieve and work with
    Claude's responses in downstream tasks.
    """
    ti = context["task_instance"]

    # Get the full response
    response = ti.xcom_pull(task_ids="simple_chat", key="claude_response")

    # Log the response details
    print(f"Claude's response: {response['content']}")
    print(f"Stop reason: {response['stop_reason']}")
    print(f"Input tokens: {response['usage']['input_tokens']}")
    print(f"Output tokens: {response['usage']['output_tokens']}")

    # Can also get just the content directly
    content = ti.xcom_pull(task_ids="simple_chat", key="claude_response_content")
    print(f"Content only: {content}")

    return {"processed": True, "content_length": len(response["content"])}


def generate_sample_document(**context):
    """Generate a sample document for analysis."""
    document = """
    Product Review Analysis - Q4 2024

    Customer Feedback Summary:

    1. Positive Feedback (65%):
    - Users love the new user interface redesign
    - Performance improvements are highly appreciated
    - Customer support response time has improved significantly
    - Integration with third-party tools works seamlessly

    2. Areas for Improvement (25%):
    - Mobile app needs better offline functionality
    - Some users report occasional sync issues
    - Pricing model could be more transparent
    - Documentation needs more examples

    3. Feature Requests (10%):
    - Dark mode for all platforms
    - Advanced analytics dashboard
    - Custom workflow automation
    - API rate limit increases

    Overall Sentiment: Positive
    NPS Score: 8.2/10
    """

    # Push to XCom for next task
    context["task_instance"].xcom_push(key="sample_document", value=document)
    return document


def process_analysis_results(**context):
    """Process the document analysis results."""
    ti = context["task_instance"]

    analysis = ti.xcom_pull(task_ids="analyze_document", key="analysis_result")

    print("=== Document Analysis Results ===")
    print(f"Analysis: {analysis['content']}")
    print(f"\nTokens used: {analysis['usage']}")

    # Save results or trigger downstream actions
    return {
        "analysis_completed": True,
        "tokens_used": analysis["usage"]["output_tokens"],
    }


# ====================
# DAG Definition
# ====================

with DAG(
    dag_id="example_bedrock_claude",
    default_args=default_args,
    description="Example DAG demonstrating AWS Bedrock and Claude integration",
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["example", "bedrock", "claude", "aws"],
) as dag:

    # ====================
    # Task 1: Simple Claude Chat
    # ====================

    simple_chat = BedrockClaudeOperator(
        task_id="simple_chat",
        messages=[
            {
                "role": "user",
                "content": "Explain Apache Airflow in 2-3 sentences. Focus on its main use cases.",
            }
        ],
        max_tokens=150,
        temperature=0.7,
        system="You are a helpful data engineering assistant. Be concise and clear.",
        output_key="claude_response",
    )

    # ====================
    # Task 2: Process Response
    # ====================

    process_response = PythonOperator(
        task_id="process_response",
        python_callable=process_claude_response,
    )

    # ====================
    # Task 3: Generate Sample Document
    # ====================

    generate_document = PythonOperator(
        task_id="generate_document",
        python_callable=generate_sample_document,
    )

    # ====================
    # Task 4: Analyze Document with Claude
    # ====================

    analyze_document = BedrockDocumentAnalysisOperator(
        task_id="analyze_document",
        document_text="{{ ti.xcom_pull(task_ids='generate_document', key='sample_document') }}",
        analysis_prompt="""
        Analyze this customer feedback document and provide:
        1. A brief summary (2-3 sentences)
        2. Top 3 strengths identified
        3. Top 3 areas for improvement
        4. One key actionable recommendation

        Format your response in clear sections.
        """,
        max_tokens=500,
        output_key="analysis_result",
    )

    # ====================
    # Task 5: Process Analysis Results
    # ====================

    process_analysis = PythonOperator(
        task_id="process_analysis",
        python_callable=process_analysis_results,
    )

    # ====================
    # Task 6: Advanced Claude Usage - Multi-turn Conversation
    # ====================

    multi_turn_analysis = BedrockClaudeOperator(
        task_id="multi_turn_analysis",
        messages=[
            {
                "role": "user",
                "content": "I'm building a data pipeline in Airflow. What are the key best practices?",
            },
        ],
        max_tokens=300,
        temperature=0.5,
        system="You are an expert Airflow architect. Provide practical, actionable advice.",
        output_key="best_practices_response",
    )

    # ====================
    # Task 7: Data-Driven Claude Invocation
    # ====================

    data_driven_chat = BedrockClaudeOperator(
        task_id="data_driven_chat",
        messages=[
            {
                "role": "user",
                "content": "Based on the analysis results, what should be our top priority?",
            },
            {
                "role": "assistant",
                "content": "{{ ti.xcom_pull(task_ids='analyze_document', key='analysis_result_content') }}",
            },
            {
                "role": "user",
                "content": "Can you elaborate on the most critical improvement area?",
            },
        ],
        max_tokens=200,
        temperature=0.7,
        output_key="priority_response",
    )

    # ====================
    # Task Dependencies
    # ====================

    # Simple chat flow
    simple_chat >> process_response

    # Document analysis flow
    generate_document >> analyze_document >> process_analysis

    # Advanced usage - runs in parallel
    analyze_document >> data_driven_chat

    # Best practices task runs independently
    # (no dependencies - showcases parallel execution)


# ====================
# Documentation
# ====================

dag.doc_md = """
# Bedrock Claude Integration Example

This DAG demonstrates various ways to use AWS Bedrock with Claude models in Airflow.

## Features Demonstrated

1. **Simple Chat**: Basic Claude invocation with a single message
2. **Response Processing**: Retrieving and processing Claude's responses via XCom
3. **Document Analysis**: Using the specialized DocumentAnalysisOperator
4. **Multi-turn Conversations**: Simulating conversation context
5. **Templating**: Using Jinja templates to pass data between tasks
6. **Parallel Execution**: Running independent Claude tasks in parallel

## Prerequisites

- AWS Bedrock access enabled
- Appropriate IAM permissions for Bedrock
- AWS connection configured in Airflow (aws_default)

## Usage

Trigger this DAG manually to see Claude in action:

```bash
airflow dags trigger example_bedrock_claude
```

## Cost Considerations

This DAG makes multiple Claude API calls. Monitor your AWS Bedrock costs:
- Each task uses different token limits
- Actual usage depends on response length
- Check XCom outputs for token usage statistics

## Customization

You can customize this DAG by:
- Changing the Claude model (default: Claude 3.5 Sonnet)
- Adjusting temperature and max_tokens
- Adding your own document analysis tasks
- Integrating with S3 for document storage
"""


# ====================
# Task Documentation
# ====================

simple_chat.doc_md = """
Simple chat task demonstrating basic Claude invocation.

**Configuration:**
- Temperature: 0.7 (balanced creativity/consistency)
- Max tokens: 150
- System prompt: Data engineering assistant

**XCom Outputs:**
- `claude_response`: Full response dictionary
- `claude_response_content`: Just the text content
- `claude_response_usage`: Token usage statistics
"""

analyze_document.doc_md = """
Document analysis task using specialized operator.

This task demonstrates how to:
1. Receive a document via XCom (templating)
2. Send it to Claude for analysis
3. Get structured analysis results

**Analysis Includes:**
- Summary
- Strengths
- Improvements
- Recommendations
"""
