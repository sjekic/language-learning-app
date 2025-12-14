# Unit Tests

This directory contains unit tests for the language learning app project.

## Configuration Files

- **`pytest.ini`**: Main configuration file for pytest. It processes options like verbose output (`-v`) and coverage settings (`--cov`) automatically. It also defines that tests are located in this `tests/` directory.
- **`conftest.py`**: Contains shared fixtures and mocks used across multiple test files. This includes mocks for:
    - Database connections (`asyncpg`)
    - Firebase Authentication
    - Azure Blob Storage & Container Instances
    - HTTP Client (`httpx`)

## Setup

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Install service dependencies (required for mocks to work):
```bash
pip install -r services/auth-service/requirements.txt
pip install -r services/user-service/requirements.txt
pip install -r services/translation-service/requirements.txt
pip install -r services/book-service/requirements.txt
pip install -r jobs/requirements.txt
```

## Running Tests

**Important**: Because the services are independent and manipulate `sys.path`, you should run tests for each service individually to avoid import conflicts.

### Run Individual Service Tests
```bash
# Auth Service
pytest --cov=services/auth-service tests/test_auth_service.py -v

# User Service
pytest --cov=services/user-service tests/test_user_service.py -v

# Translation Service
pytest --cov=services/translation-service tests/test_translation_service.py -v

# Book Service
pytest --cov=services/book-service tests/test_book_service.py -v

# Background Jobs
pytest --cov=jobs/src tests/test_jobs.py -v

# Integration (cross-service, in-memory)
./venv/bin/python -m pytest tests/test_integration_services.py -v --no-cov
```

## Coverage Reports

Coverage is calculated automatically when running the commands above.
- **Terminal**: Shows a summary table after the tests run.
- **HTML Report**: Detailed report generated in `htmlcov/index.html`.

To ensure >70% coverage (will fail if below):
```bash
pytest --cov-fail-under=70 --cov=services/auth-service tests/test_auth_service.py
```

## Test Structure

- `tests/test_auth_service.py`: Authentication API & Firebase logic
- `tests/test_user_service.py`: User profile & management API
- `tests/test_translation_service.py`: Translation API & caching
- `tests/test_book_service.py`: Book generation API & Azure storage integration
- `tests/test_jobs.py`: Background job processing logic
- `tests/test_integration_services.py`: Auth → translation (vocab) → user flow using shared in-memory fakes (run with --no-cov)

## Mocks & Isolation

- **Database**: We use `mock_db` context managers and `asyncpg` mocks to simulate database operations without a real Postgres instance.
- **External APIs**: Calls to Azure, Firebase, and Translation APIs are mocked to ensure tests are fast, reliable, and cost-free.
