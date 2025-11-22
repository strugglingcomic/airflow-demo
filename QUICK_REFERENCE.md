# Test Harness Quick Reference Card

## 🚀 Quick Commands

```bash
# Installation
pip install -e ".[dev]"
pre-commit install

# Run Tests
make test              # All tests
make test-unit         # Fast unit tests
make test-coverage     # With coverage report

# Quality
make lint              # Check code
make format            # Format code
make quality           # All checks

# Development
make test-watch        # Auto-run tests on file changes
pytest -k s3 tests/    # Run S3 tests only
pytest --lf tests/     # Run last failed
```

## 📊 Test Categories

| Command | Tests | Speed | Purpose |
|---------|-------|-------|---------|
| `pytest -m unit` | ~300 | <30s | Individual methods |
| `pytest -m integration` | ~150 | ~1min | Service interactions |
| `pytest -m e2e` | ~50 | ~2min | Full DAG runs |
| `make test` | ~500 | ~2min | Everything |

## 🎯 TDD Red-Green-Refactor

```python
# 1. RED - Write failing test
def test_my_feature(s3_client, s3_bucket):
    service = S3Service()
    result = service.my_method()
    assert result == expected

# 2. GREEN - Make it pass
def my_method(self):
    return expected

# 3. REFACTOR - Improve while staying green
def my_method(self):
    # Better implementation
    return self._helper_method()
```

## 🔧 Common Fixtures

```python
# AWS
s3_client, s3_bucket, s3_bucket_with_data
bedrock_client, bedrock_model_id
secrets_client, sample_secrets

# Airflow
sample_dag, task_instance, airflow_context, dag_bag

# Data
sample_json_data, sample_csv_data, faker_instance

# Utils
temp_dir, temp_file, frozen_time, performance_timer
```

## 📝 Test Template

```python
import pytest

@pytest.mark.unit
@pytest.mark.s3
def test_feature_name(s3_client, s3_bucket):
    """Test description."""
    # ARRANGE
    service = S3Service()
    service.client = s3_client

    # ACT
    result = service.method(s3_bucket, "key")

    # ASSERT
    assert result == expected
    assert service.object_exists(s3_bucket, "key")
```

## 🎓 Learning Path

1. **[TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)** → 5 min start
2. **[TDD_WORKFLOW_GUIDE.md](docs/TDD_WORKFLOW_GUIDE.md)** → Complete tutorial
3. **[tests/unit/services/test_s3_service.py](tests/unit/services/test_s3_service.py)** → Examples
4. **[TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)** → Deep dive

## 🔍 Debugging Tests

```bash
pytest tests/file.py::test_name -v     # Specific test
pytest tests/ -s                       # Show prints
pytest tests/ --pdb                    # Drop to debugger
pytest tests/ -vv                      # Very verbose
pytest tests/ -x                       # Stop on first failure
pytest tests/ --lf                     # Last failed only
pytest tests/ --durations=10           # Show 10 slowest
```

## 📈 Coverage

```bash
# Generate report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html

# Check threshold
pytest --cov=src --cov-fail-under=80 tests/

# Show missing lines
pytest --cov=src --cov-report=term-missing tests/
```

## 🎯 Test Markers

```bash
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests
pytest -m e2e              # End-to-end tests
pytest -m s3               # S3 tests
pytest -m bedrock          # Bedrock tests
pytest -m "not slow"       # Skip slow tests
pytest -m "s3 or bedrock"  # Multiple markers
```

## 🛠️ Test Helpers

```python
from tests.utils.test_helpers import (
    S3TestHelper,
    BedrockTestHelper,
    SecretsTestHelper,
    DataBuilder,
    AssertionHelper,
)

# S3
response = S3TestHelper.create_s3_object(bucket, key, content)

# Bedrock
response = BedrockTestHelper.create_invoke_response("Hello!")
chunks = BedrockTestHelper.create_streaming_chunks("Response")

# Assertions
AssertionHelper.assert_s3_object_exists(s3_client, bucket, key)
AssertionHelper.assert_bedrock_response_valid(response)

# Data
builder = DataBuilder()
user = builder.build_user(name="John")
dataset = builder.build_dataset("build_user", count=100)
```

## 🔄 Git Workflow

```bash
# Start feature
git checkout -b feature/my-feature

# TDD cycle
vim tests/unit/services/test_s3_service.py  # Write test
pytest tests/...::test_name -v               # See it fail
vim src/airflow_demo/services/s3_service.py # Implement
pytest tests/...::test_name -v               # See it pass

# Before commit
make test-coverage          # Check coverage
make quality               # Run quality checks

# Commit (pre-commit runs automatically)
git commit -m "Add feature with tests"
```

## 📦 Project Structure

```
src/airflow_demo/          # Source code
  services/                # ← Implement here
  operators/
  hooks/

tests/                     # Test suite
  unit/                    # ← Write tests here first
  integration/
  e2e/
  conftest.py             # ← Fixtures defined here
  utils/test_helpers.py   # ← Helpers here
```

## 🎯 Coverage Targets

| Component | Target |
|-----------|--------|
| Services | 95% |
| Operators | 90% |
| Hooks | 85% |
| DAGs | 80% |
| Overall | 85% |

## 🚨 Common Issues

**Import Error**: `pip install -e .`

**Fixture Not Found**: Check `tests/conftest.py`

**Slow Tests**: `pytest -m "not slow" tests/`

**Mocking Not Working**: Patch at point of use, not definition

## 📞 Help

- **Quick Start**: [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md)
- **TDD Guide**: [docs/TDD_WORKFLOW_GUIDE.md](docs/TDD_WORKFLOW_GUIDE.md)
- **Test Docs**: [tests/README.md](tests/README.md)
- **Strategy**: [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)

## 💡 Pro Tips

✅ Write test FIRST (TDD!)
✅ Keep tests independent
✅ Use descriptive names
✅ One assertion per test (usually)
✅ Test error cases
✅ Run tests frequently
✅ Use fixtures for setup
✅ Mock external services
✅ Keep tests fast

---

**Print this page for your desk!** 📌

Quick access: `/home/user/airflow-demo/QUICK_REFERENCE.md`
