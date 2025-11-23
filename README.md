# Apache Airflow 2.10.5 + AWS Integration Demo

A modern, production-ready Apache Airflow repository for testing and prototyping AWS integration patterns with comprehensive TDD infrastructure.

## 🎯 Project Overview

This repository serves as a **testing ground for Apache Airflow 2.x and AWS integration ideas**, featuring:

- **Apache Airflow 2.10.5** (latest 2.x - NOT 3.x)
- **AWS Service Integration**: S3, Secrets Manager, IAM, Bedrock (Claude SDK)
- **uv Package Manager**: Modern, Rust-based package manager (10-100x faster than pip)
- **Comprehensive Test Suite**: Unit + Integration tests with moto (AWS mocking)
- **TDD Methodology**: Test-Driven Development throughout
- **Production-Ready Patterns**: CI/CD, pre-commit hooks, quality gates

## 🚨 CRITICAL: Package Manager

**This project EXCLUSIVELY uses `uv`/`uvx` package manager.**

### ❌ DO NOT USE:
- pip, venv, virtualenv, poetry, pipenv, conda, or any other package manager
- Raw python/python3 commands

### ✅ ALWAYS USE:
- `uv` for all package operations
- `uvx` for running tools
- `uv run` for executing scripts

See [Claude.md](Claude.md) for detailed uv usage instructions.

## 🚀 Quick Start

### Prerequisites

Install uv:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

### Installation

```bash
# Clone the repository
cd /home/user/airflow-demo

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install all dependencies (including dev dependencies)
uv pip install -e ".[dev,test]"

# Set up pre-commit hooks
uv run pre-commit install
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only (fast)
uv run pytest tests/unit -m unit

# Run integration tests
uv run pytest tests/integration -m integration

# Run with coverage report
uv run pytest --cov=src --cov=plugins --cov-report=html

# Open coverage report
open htmlcov/index.html

# Alternatively, use make commands
make test              # Run all tests
make test-unit         # Unit tests only
make test-coverage     # With coverage HTML report
```

### Your First Test

```python
# tests/unit/services/test_my_service.py
import pytest

@pytest.mark.unit
def test_my_feature(s3_client, s3_bucket):
    """Test my new S3 feature."""
    from src.airflow_demo.services.s3_service import S3Service

    service = S3Service()
    service.client = s3_client

    # Your test here
    result = service.my_new_method(s3_bucket, "test.txt")
    assert result == "expected_output"
```

Run it:
```bash
pytest tests/unit/services/test_my_service.py::test_my_feature -v
```

## 📚 Documentation

### Getting Started
- **[Testing Quick Start](TESTING_QUICKSTART.md)** - Get up and running in 5 minutes
- **[TDD Workflow Guide](docs/TDD_WORKFLOW_GUIDE.md)** - Complete TDD tutorial with examples
- **[Testing Strategy](docs/TESTING_STRATEGY.md)** - Overall testing approach and philosophy

### Detailed References
- **[Test Suite README](tests/README.md)** - All fixtures, helpers, and test organization
- **[Makefile Commands](#makefile-commands)** - All available make commands

## 🧪 Test Infrastructure

### Test Pyramid

```
        /\
       /  \     E2E Tests (~50)
      /----\    Full DAG execution
     /      \   10-60s each
    /--------\
   /          \ Integration Tests (~150)
  /------------\ Service integration
 /              \ 1-10s each
/________________\
   Unit Tests (~300)
   Isolated components
   <1s each
```

### Test Categories

| Category | Count | Speed | Coverage |
|----------|-------|-------|----------|
| **Unit** | ~300 | <1s | Individual methods |
| **Integration** | ~150 | 1-10s | Service interactions |
| **E2E** | ~50 | 10-60s | Complete workflows |

### Key Features

✅ **Comprehensive Fixtures**
- AWS service mocks (S3, Bedrock, Secrets Manager)
- Airflow test fixtures (DAGs, tasks, context)
- Test data generators (JSON, CSV, Faker)

✅ **Test Helpers**
- S3TestHelper, BedrockTestHelper, SecretsTestHelper
- Mock response builders
- Common assertions
- Data builders

✅ **Quality Gates**
- 85%+ code coverage requirement
- Pre-commit hooks (format, lint, type check, tests)
- CI/CD integration (GitHub Actions)
- Security scanning (bandit)

✅ **Fast Feedback**
- Unit tests run in < 30 seconds
- Parallel test execution
- Watch mode for development
- Incremental testing

## 🏗️ Project Structure

```
airflow-demo/
├── src/airflow_demo/              # Source code
│   ├── services/                  # Service layer
│   │   ├── s3_service.py         # S3 operations
│   │   ├── bedrock_service.py    # Bedrock/AI operations
│   │   └── secrets_service.py    # Secrets Manager
│   ├── operators/                 # Custom Airflow operators
│   ├── hooks/                     # Custom Airflow hooks
│   └── config/                    # Configuration management
│
├── tests/                         # Test suite
│   ├── conftest.py               # Root fixtures
│   ├── unit/                     # Unit tests (60%)
│   │   ├── services/
│   │   ├── operators/
│   │   └── hooks/
│   ├── integration/              # Integration tests (30%)
│   │   └── aws/
│   ├── e2e/                      # End-to-end tests (10%)
│   ├── fixtures/                 # Test data and sample DAGs
│   │   ├── dags/
│   │   └── data/
│   └── utils/                    # Test utilities
│       └── test_helpers.py
│
├── docs/                          # Documentation
│   ├── TDD_WORKFLOW_GUIDE.md     # Complete TDD tutorial
│   └── TESTING_STRATEGY.md       # Testing philosophy
│
├── .github/workflows/             # CI/CD
│   └── test.yml                  # GitHub Actions workflow
│
├── Makefile                       # Common commands
├── pyproject.toml                # Project configuration
├── .pre-commit-config.yaml       # Pre-commit hooks
└── TESTING_QUICKSTART.md         # Quick start guide
```

## 🔧 Development Workflow

### TDD Red-Green-Refactor Cycle

```bash
# 1. RED - Write a failing test
vim tests/unit/services/test_s3_service.py
pytest tests/unit/services/test_s3_service.py::test_new_feature -v
# ❌ FAILS (expected)

# 2. GREEN - Make it pass
vim src/airflow_demo/services/s3_service.py
pytest tests/unit/services/test_s3_service.py::test_new_feature -v
# ✅ PASSES

# 3. REFACTOR - Improve the code
vim src/airflow_demo/services/s3_service.py
pytest tests/unit/services/test_s3_service.py -v
# ✅ STILL PASSES

# 4. Commit
git add .
git commit -m "Add new feature with tests"
# Pre-commit hooks run automatically
```

### Daily Development

```bash
# Start your day
git pull
make test-unit          # Ensure everything works

# Work on a feature (TDD)
make test-watch        # Keep tests running

# Check your work
make test-coverage     # Verify coverage
make quality          # Run quality checks

# Commit (pre-commit hooks run automatically)
git commit -m "Your changes"
```

## 🎯 Makefile Commands

### Testing
```bash
make test              # Run all tests
make test-unit         # Unit tests only (fast)
make test-integration  # Integration tests
make test-e2e         # End-to-end tests
make test-fast        # Skip slow tests
make test-coverage    # Tests with coverage report
make test-watch       # Watch mode (re-run on changes)
make test-parallel    # Run tests in parallel

# By service
make test-s3          # S3 tests only
make test-bedrock     # Bedrock tests only
make test-secrets     # Secrets Manager tests only
make test-dag         # DAG tests only
```

### Quality
```bash
make lint             # Run linters
make format           # Format code
make typecheck        # Type checking
make quality          # All quality checks
```

### CI/CD
```bash
make ci               # Run full CI pipeline locally
make ci-test          # CI test suite
make ci-quality       # CI quality checks
```

### Utilities
```bash
make help             # Show all commands
make clean            # Clean temporary files
make stats            # Show test statistics
```

## 📊 Test Examples

### Unit Test Example

```python
@pytest.mark.unit
@pytest.mark.s3
def test_s3_upload_file(s3_client, s3_bucket, temp_file):
    """Test successful file upload to S3."""
    service = S3Service()
    service.client = s3_client

    result = service.upload_file(temp_file, s3_bucket, "test.txt")

    assert result == f"s3://{s3_bucket}/test.txt"
    assert service.object_exists(s3_bucket, "test.txt")
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.aws
def test_s3_to_bedrock_workflow(s3_client, bedrock_client, s3_bucket):
    """Test complete workflow: S3 → Bedrock → S3."""
    s3_service = S3Service()
    bedrock_service = BedrockService()

    # Upload document to S3
    s3_service.write_json({"text": "AI document"}, s3_bucket, "doc.json")

    # Read and analyze
    doc = s3_service.read_json(s3_bucket, "doc.json")
    analysis = bedrock_service.analyze_document(doc["text"], "Summarize")

    # Write results
    s3_service.write_json({"analysis": analysis}, s3_bucket, "result.json")

    # Verify
    result = s3_service.read_json(s3_bucket, "result.json")
    assert "analysis" in result
```

### E2E DAG Test Example

```python
@pytest.mark.e2e
@pytest.mark.dag
def test_document_analysis_dag(document_analysis_dag, execution_date):
    """Test complete DAG execution."""
    # Test DAG structure
    assert len(document_analysis_dag.tasks) == 3

    # Test task dependencies
    assert dag.get_task("analyze_with_bedrock") in \
           dag.get_task("read_from_s3").downstream_list

    # Execute and verify
    # ... (see tests/e2e/test_document_analysis_dag.py for full example)
```

## 🔍 Available Fixtures

### AWS Services
- `s3_client`, `s3_resource` - Mocked S3
- `s3_bucket`, `s3_bucket_with_data` - Test buckets
- `secrets_client`, `sample_secrets` - Secrets Manager
- `bedrock_client`, `bedrock_model_id` - Bedrock AI
- `bedrock_streaming_response` - Mock streaming

### Airflow
- `sample_dag` - Test DAG
- `task_instance` - Task instance
- `airflow_context` - Execution context
- `dag_bag` - DAG bag

### Test Data
- `sample_json_data`, `sample_csv_data` - Sample data
- `large_json_dataset` - Performance testing
- `faker_instance` - Data generation

### Utilities
- `temp_dir`, `temp_file` - Temporary files
- `frozen_time` - Time manipulation
- `performance_timer` - Performance measurement
- `metrics_collector` - Metrics tracking

See [tests/README.md](tests/README.md) for complete fixture documentation.

## 🎓 Learning Resources

### For Beginners
1. Start with [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)
2. Follow the [TDD Workflow Guide](docs/TDD_WORKFLOW_GUIDE.md)
3. Explore example tests in `tests/unit/services/`

### For Intermediate
1. Review [Testing Strategy](docs/TESTING_STRATEGY.md)
2. Study integration tests in `tests/integration/`
3. Examine test helpers in `tests/utils/test_helpers.py`

### For Advanced
1. Review E2E tests in `tests/e2e/`
2. Study CI/CD configuration in `.github/workflows/`
3. Explore performance testing patterns

## 📈 Coverage Goals

| Component | Target | Critical Paths |
|-----------|--------|----------------|
| Services | 95% | 100% |
| Operators | 90% | 95% |
| Hooks | 85% | 90% |
| DAGs | 80% | 85% |
| **Overall** | **85%** | **90%** |

## 🔐 CI/CD Pipeline

### Automated Checks (on every PR)

✅ Code Quality
- Linting (ruff)
- Formatting (black)
- Type checking (mypy)

✅ Testing
- Unit tests (Python 3.10, 3.11, 3.12)
- Integration tests
- E2E tests
- Coverage reporting

✅ Security
- Dependency scanning (safety)
- Code scanning (bandit)

### Pre-Commit Hooks (on every commit)

Automatically runs:
1. Code formatting
2. Linting
3. Type checking
4. Fast unit tests
5. Security scan

## 🤝 Contributing

### Adding a New Feature (TDD Approach)

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Write test FIRST
# tests/unit/services/test_s3_service.py
@pytest.mark.unit
@pytest.mark.s3
def test_my_new_feature(s3_client, s3_bucket):
    service = S3Service()
    result = service.my_new_method(...)
    assert result == expected

# 3. Run test (should fail)
pytest tests/unit/services/test_s3_service.py::test_my_new_feature -v

# 4. Implement feature
# src/airflow_demo/services/s3_service.py
def my_new_method(self, ...):
    # Implementation
    ...

# 5. Run test (should pass)
pytest tests/unit/services/test_s3_service.py::test_my_new_feature -v

# 6. Run all related tests
pytest -m s3 tests/ -v

# 7. Check coverage
make test-coverage

# 8. Commit (pre-commit hooks run)
git commit -m "Add new feature with tests"
```

## 🐛 Troubleshooting

### Common Issues

**Tests not found:**
```bash
pip install -e .
```

**Import errors:**
```bash
pip install -e ".[dev]"
```

**Slow tests:**
```bash
pytest -m "not slow" tests/  # Skip slow tests
pytest -n auto tests/        # Run in parallel
```

**Coverage too low:**
```bash
pytest --cov=src --cov-report=term-missing tests/
# Identifies lines not covered
```

## 📞 Getting Help

- **Quick Start**: [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)
- **TDD Tutorial**: [docs/TDD_WORKFLOW_GUIDE.md](docs/TDD_WORKFLOW_GUIDE.md)
- **Test Docs**: [tests/README.md](tests/README.md)
- **Strategy**: [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)

## 📄 License

See [LICENSE](LICENSE) for details.

## 🌟 Features Highlights

✨ **500+ Comprehensive Tests**
✨ **85%+ Code Coverage**
✨ **TDD-Driven Development**
✨ **Fast Feedback Loop (<30s for unit tests)**
✨ **Realistic AWS Mocking (moto)**
✨ **Complete DAG Testing**
✨ **CI/CD Ready**
✨ **Production-Ready Structure**

---

**Start Testing Today!** 🚀

```bash
pip install -e ".[dev]"
make test
```

Built with ❤️ using Test-Driven Development
