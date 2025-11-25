# BridgeAI Backend Test Suite

This directory contains comprehensive tests for the BridgeAI backend application.

## Test Coverage

- **73 total tests** covering all major functionality
- Authentication & Authorization
- Team Management
- Project Management & Approval Workflow
- Invitations
- Notifications
- Rate Limiting

## Prerequisites

Make sure you have the virtual environment activated and all dependencies installed:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run All Tests with Verbose Output

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
# Authentication tests
pytest tests/test_auth.py -v

# Team tests
pytest tests/test_teams.py -v

# Project tests
pytest tests/test_projects.py -v

# Invitation tests
pytest tests/test_invitations.py -v

# Notification tests
pytest tests/test_notifications.py -v

# Rate limit tests
pytest tests/test_rate_limit.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestUserRegistration -v
```

### Run Specific Test

```bash
pytest tests/test_auth.py::TestUserRegistration::test_register_client_user -v
```

### Run Tests with Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
```

### Run Tests and Stop on First Failure

```bash
pytest tests/ -x
```

### Run Tests with Short Traceback

```bash
pytest tests/ --tb=short
```

### Run Tests in Parallel (faster)

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_auth.py             # Authentication endpoint tests (14 tests)
├── test_teams.py            # Team management tests (15 tests)
├── test_projects.py         # Project management tests (14 tests)
├── test_invitations.py      # Invitation workflow tests (14 tests)
├── test_notifications.py    # Notification tests (12 tests)
└── test_rate_limit.py       # Rate limiting tests (4 tests)
```

## Test Fixtures

The `conftest.py` file provides shared fixtures:

- `db`: Fresh database session for each test
- `client`: FastAPI test client
- `test_ba_user`: Business Analyst user
- `test_client_user`: Client user
- `test_another_client_user`: Additional client user
- `ba_auth_headers`: Authentication headers for BA user
- `client_auth_headers`: Authentication headers for client user
- `another_client_auth_headers`: Authentication headers for another client user

## Test Database

Tests use an in-memory SQLite database that is created fresh for each test, ensuring:
- Fast test execution
- Complete isolation between tests
- No impact on production/development databases

## Common Issues

### Rate Limiting Tests Failing

If rate limit tests fail, they might be hitting actual rate limits. The test suite resets rate limits between tests, but if you run individual rate limit tests multiple times quickly, you may hit limits.

**Solution**: Wait a few minutes or restart the test suite.

### Import Errors

If you see import errors, make sure you're in the project root and the virtual environment is activated:

```bash
cd /home/abdelrahman/project/bridgeai-backend
source venv/bin/activate
pytest tests/
```

### Database Issues

Tests create a fresh in-memory database for each test. If you encounter database-related issues:

1. Make sure all migrations are up to date
2. Check that database models are properly imported in `conftest.py`
3. Verify that the test database is being properly created and torn down

## Writing New Tests

When adding new tests:

1. Use the existing fixtures from `conftest.py`
2. Follow the class-based organization pattern
3. Use descriptive test names that explain what is being tested
4. Include docstrings for complex tests
5. Test both success and failure cases
6. Verify proper authentication and authorization

Example test structure:

```python
class TestNewFeature:
    """Test new feature functionality."""

    def test_success_case(self, client, client_auth_headers):
        """Test that feature works correctly."""
        response = client.post("/api/feature/", 
            json={"data": "value"},
            headers=client_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["data"] == "value"

    def test_unauthorized_access(self, client):
        """Test that unauthenticated users cannot access."""
        response = client.post("/api/feature/", json={"data": "value"})
        assert response.status_code == 401
```

## CI/CD Integration

To integrate with CI/CD pipelines:

```bash
# GitHub Actions example
pytest tests/ --tb=short --cov=app --cov-report=xml

# GitLab CI example
pytest tests/ --tb=short --junitxml=report.xml
```

## Performance

Current test suite performance:
- **73 tests** complete in approximately **~2 minutes**
- Tests run sequentially by default
- Can be parallelized with `pytest-xdist` for faster execution

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
