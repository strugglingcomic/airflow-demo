# Airflow Demo Repository

## Purpose

This repository is a **testing ground for Apache Airflow 2.x ideas and AWS integration patterns**. It serves as a modern, production-ready foundation for:

- Experimenting with Apache Airflow 2.10.5 (latest 2.x) workflows
- Integrating AWS services (S3, Secrets Manager, IAM, Bedrock) with Airflow
- Testing data pipelines and ETL workflows in a controlled environment
- Developing and validating custom Airflow operators, hooks, and sensors
- Prototyping ML workflows using AWS Bedrock and Claude SDK
- Following TDD (Test-Driven Development) best practices for data engineering

## Project Stack

- **Airflow Version**: 2.10.5 (latest 2.x - NOT 3.x)
- **Python Version**: 3.11+
- **Package Manager**: **uv/uvx exclusively** (see below)
- **AWS Services**: S3, Secrets Manager, IAM, Bedrock (Claude)
- **Testing**: pytest, moto (AWS mocking), pytest-mock
- **Code Quality**: ruff, black, mypy

## AWS Architecture

This repository is designed for **hypothetical AWS deployment** with the following primitives:

- **S3**: Data storage, logs, artifacts
- **AWS Secrets Manager**: Secrets and connection management
- **IAM Roles**: Permission management (no hardcoded credentials)
- **AWS Bedrock**: Claude SDK integration for AI/ML workflows
- **Local Testing**: Comprehensive mocking with `moto` - no real AWS resources required for development

## Package Manager: uv/uvx ONLY

### 🚨 CRITICAL REQUIREMENT 🚨

This project **EXCLUSIVELY uses the `uv`/`uvx` package manager**.

### ❌ DO NOT USE:
- ❌ `pip` / `pip install`
- ❌ `python -m venv` / `venv`
- ❌ `python3` / `python` commands directly
- ❌ `virtualenv`
- ❌ `poetry` / `pipenv` / `conda`
- ❌ Any other package manager

### ✅ ALWAYS USE:
- ✅ `uv` for all package operations
- ✅ `uvx` for running tools
- ✅ `uv run` for executing Python scripts
- ✅ `uv pip` for pip-compatible operations (if absolutely necessary)

## Why uv?

`uv` is a modern, **Rust-based Python package manager** that is:
- **10-100x faster** than pip
- **More reliable** with deterministic dependency resolution
- **Simpler** with unified workflows
- **Production-ready** with lockfile support (uv.lock)

Learn more: https://docs.astral.sh/uv/

---

## Quick Start

### 1. Install uv (if not already installed)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**
```bash
uv --version
```

### 2. Set Up Development Environment

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

### 3. Verify Installation

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit -m unit

# Check code quality
uv run ruff check .
uv run black --check .
uv run mypy src plugins
```

### 4. Run Airflow Locally (Docker)

```bash
# Start Airflow stack
cd docker
docker-compose up -d

# Access Airflow UI
# http://localhost:8080
# Username: admin
# Password: admin

# Stop Airflow
docker-compose down
```

---

## Development Workflow with uv

### Installing Dependencies

```bash
# Add a new dependency
uv pip install <package-name>

# Add a development dependency
uv pip install <package-name> --dev

# Install from requirements file (if needed)
uv pip install -r requirements.txt

# Sync dependencies (recommended)
uv pip sync
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov=plugins --cov-report=html

# Run specific test file
uv run pytest tests/unit/services/test_s3_service.py -v

# Run tests with specific marker
uv run pytest -m unit        # Unit tests only
uv run pytest -m integration # Integration tests only
uv run pytest -m aws         # AWS-related tests

# Run tests in parallel (faster)
uv run pytest -n auto
```

### Code Quality Tools

```bash
# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run black .

# Check formatting without modifying
uv run black --check .

# Type checking
uv run mypy src plugins

# Run all quality checks
uv run ruff check . && uv run black --check . && uv run mypy src plugins
```

### Running Python Scripts

```bash
# Run a Python script
uv run python scripts/validate_dags.py

# Run a Python module
uv run -m pytest

# Execute a one-off command with uvx
uvx ruff check .
```

---

## Project Structure

```
airflow-demo/
├── dags/                      # Airflow DAG definitions
│   ├── examples/              # Example DAGs
│   ├── etl/                   # ETL pipeline DAGs
│   └── ml/                    # ML workflow DAGs
├── plugins/                   # Airflow plugins
│   ├── operators/             # Custom operators
│   ├── hooks/                 # Custom hooks
│   ├── sensors/               # Custom sensors
│   └── utils/                 # Utility functions
├── src/                       # Source code (service layer)
│   └── airflow_aws/
│       ├── config/            # Configuration management
│       ├── services/          # AWS service wrappers
│       └── models/            # Data models
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests (with moto)
│   ├── e2e/                   # End-to-end tests
│   ├── fixtures/              # Test fixtures and sample data
│   └── utils/                 # Test utilities
├── config/                    # Configuration files
├── scripts/                   # Utility scripts
├── docker/                    # Docker configuration
├── pyproject.toml             # Project configuration (uv)
├── uv.lock                    # Dependency lockfile
└── Claude.md                  # This file
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp config/.env.example .env
```

Key variables:
- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_S3_BUCKET_DATA`: S3 data bucket name
- `AWS_S3_BUCKET_LOGS`: S3 logs bucket name
- `AWS_SECRETS_PREFIX`: Secrets Manager path prefix
- `AIRFLOW_HOME`: Airflow home directory
- `AIRFLOW__CORE__EXECUTOR`: Airflow executor type

### Airflow Configuration

Airflow configuration is managed through:
1. Environment variables (`AIRFLOW__SECTION__KEY`)
2. `config/airflow.cfg` (local overrides)
3. AWS Secrets Manager (production secrets)

---

## Testing Strategy

This project follows **TDD (Test-Driven Development)** principles:

1. **Write tests FIRST** (RED phase)
2. **Implement minimal code** to pass tests (GREEN phase)
3. **Refactor** while keeping tests green (REFACTOR phase)

### Test Categories

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test AWS service integrations with moto
- **E2E Tests** (`tests/e2e/`): Test complete DAG executions

### Coverage Requirements

- **Overall**: 85%+ coverage
- **Services**: 100% coverage required
- **Hooks/Operators**: 90%+ coverage
- **DAGs**: 80%+ coverage (structure and validation)

---

## AWS Services & Mocking

### Local Development (No Real AWS)

All AWS services are **mocked using `moto`** for local development and testing:

```python
import boto3
from moto import mock_aws

@mock_aws
def test_s3_operation():
    # This S3 client is fully mocked - no real AWS calls
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    # ... test your code
```

### AWS Services Integration

- **S3Service** (`src/airflow_aws/services/s3_service.py`): S3 operations
- **SecretsService** (`src/airflow_aws/services/secrets_service.py`): Secrets Manager
- **BedrockService** (`src/airflow_aws/services/bedrock_service.py`): Bedrock/Claude integration
- **IAMService** (TODO): IAM role management

---

## Best Practices

### 1. Always Use uv

```bash
# ❌ WRONG
pip install apache-airflow

# ✅ CORRECT
uv pip install apache-airflow
```

### 2. Use Virtual Environments

```bash
# Create venv with uv
uv venv

# Activate it
source .venv/bin/activate
```

### 3. Keep Dependencies Locked

```bash
# After adding dependencies, regenerate lock file
uv pip compile pyproject.toml -o requirements.txt

# Or use uv's native locking (if available)
uv lock
```

### 4. Write Tests First (TDD)

```bash
# 1. Write test
vim tests/unit/services/test_new_feature.py

# 2. Run test (should fail)
uv run pytest tests/unit/services/test_new_feature.py

# 3. Implement feature
vim src/airflow_aws/services/new_feature.py

# 4. Run test (should pass)
uv run pytest tests/unit/services/test_new_feature.py
```

### 5. Use Pre-commit Hooks

Pre-commit hooks automatically run linting, formatting, and tests:

```bash
# Install hooks
uv run pre-commit install

# Manually run hooks
uv run pre-commit run --all-files
```

---

## Common Commands

### Development

```bash
# Install dependencies
uv pip install -e ".[dev,test]"

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov=plugins --cov-report=html

# Format code
uv run black .

# Lint code
uv run ruff check --fix .

# Type check
uv run mypy src plugins
```

### Airflow

```bash
# Initialize Airflow database
uv run airflow db init

# Create admin user
uv run airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Run scheduler
uv run airflow scheduler

# Run webserver
uv run airflow webserver
```

### Docker

```bash
# Start Airflow stack
cd docker && docker-compose up -d

# View logs
docker-compose logs -f airflow-scheduler

# Stop stack
docker-compose down

# Rebuild images
docker-compose build
```

---

## Contributing

1. Create a feature branch
2. Write tests FIRST (TDD)
3. Implement feature
4. Ensure all tests pass: `uv run pytest`
5. Ensure code quality: `uv run ruff check . && uv run black .`
6. Commit and push

---

## Resources

### uv Documentation
- Official Docs: https://docs.astral.sh/uv/
- GitHub: https://github.com/astral-sh/uv
- Installation Guide: https://docs.astral.sh/uv/getting-started/installation/

### Apache Airflow
- Airflow 2.10 Docs: https://airflow.apache.org/docs/apache-airflow/2.10.5/
- Best Practices: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
- AWS Provider: https://airflow.apache.org/docs/apache-airflow-providers-amazon/

### AWS Integration
- Moto (AWS Mocking): https://docs.getmoto.org/
- AWS Secrets Manager Backend: https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/secrets-backends/aws-secrets-manager.html
- Boto3 Documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

### Testing
- pytest: https://docs.pytest.org/
- pytest-mock: https://pytest-mock.readthedocs.io/
- moto: https://docs.getmoto.org/

---

## Troubleshooting

### uv not found

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
export PATH="$HOME/.cargo/bin:$PATH"
```

### Import errors

```bash
# Reinstall in editable mode
uv pip install -e ".[dev,test]"
```

### Tests failing

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv pip install -e ".[dev,test]"

# Clear pytest cache
uv run pytest --cache-clear
```

### AWS mocking issues

```bash
# Ensure moto is installed with all extras
uv pip install "moto[all]"
```

---

## License

This is a demo/testing repository. Use at your own discretion.

---

## Support

For questions or issues:
1. Check this Claude.md file first
2. Review test examples in `tests/` directory
3. Consult Airflow documentation
4. Review uv documentation

---

**Remember: Always use `uv`/`uvx` - never pip or other package managers!**
