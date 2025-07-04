.. _testing_guide:

Testing Guide
============

This guide covers how to run and write tests for the Trustworthiness Detector.

Running Tests
------------

Run all tests:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

Run a specific test file:
```bash
pytest tests/unit/test_metrics.py -v
```

Run tests with coverage report:
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

Test Organization
----------------

Tests are organized as follows:
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests
- `tests/e2e/` - End-to-end tests

Writing Tests
------------

1. **Unit Tests**
   - Test one component in isolation
   - Use mocks for external dependencies
   - Follow the naming convention `test_*.py`

Example unit test:
```python
import pytest
from unittest.mock import Mock, patch
from trustworthiness.detector import TrustworthinessDetector

@pytest.mark.asyncio
async def test_evaluate_returns_score():
    detector = TrustworthinessDetector()
    result = await detector.evaluate("Test text")
    assert 0 <= result.score <= 1.0
```

2. **Integration Tests**
   - Test interactions between components
   - Use real dependencies when possible
   - Mark with `@pytest.mark.integration`

3. **Fixtures**
   - Common test fixtures are in `tests/conftest.py`
   - Use fixtures for reusable test data and setup

Test Coverage
------------

- Aim for at least 80% test coverage
- Check coverage with:
  ```bash
  pytest --cov=src --cov-report=term-missing
  ```
- Add tests for new features and bug fixes
- Update tests when changing functionality

Mocking
-------

Use `unittest.mock` for:
- External API calls
- File I/O operations
- Database queries
- Time-dependent functions

Example:
```python
from unittest.mock import patch, MagicMock

@patch('trustworthiness.detector.requests.post')
def test_external_api_call(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"score": 0.85}
    mock_post.return_value = mock_response
    
    # Test code that makes the API call
```

Continuous Integration
---------------------

- Tests run on every push via GitHub Actions
- PRs require all tests to pass
- Coverage must not decrease

Debugging Tests
--------------

Use `pdb` for debugging:
```python
import pdb; pdb.set_trace()  # Add this line where you want to break
```

Run with `-s` to see print statements:
```bash
pytest tests/unit/test_file.py -v -s
```
