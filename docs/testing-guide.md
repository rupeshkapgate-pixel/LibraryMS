# Testing Guide

## Quick Start

```bash
# Install dependencies (once)
make test-install

# Generate proto stubs (once, or after proto changes)
make proto

# Run all tests
make test
```

## What the tests cover

| Service | Test File | Coverage |
|---------|-----------|----------|
| book-service | `test_book_repository.py` | Create, Get, Update, Delete, Availability mutations, List |
| member-service | `test_member_repository.py` | Create, Get, Update, Deactivate |
| lending-service | `test_lending.py` | Fine calculation, Create, Return on-time, Return overdue, Return already-returned, Saga compensation |
| api-gateway | `test_schemas.py` | Pydantic validation, gRPC→HTTP error mapping |

## Running specific tests

```bash
# One service
make test-book-service
make test-lending-service

# One file
cd services/lending-service
python -m pytest tests/test_lending.py::TestSagaCompensation -v

# One test
python -m pytest tests/test_lending.py::TestFineCalculation::test_fine_formula -v
```

## Test philosophy

- All tests use `unittest.mock` — no real database or gRPC connections needed.
- Tests run with `python -m pytest` from each service directory.
- The `conftest.py` in each service adds the service root to `sys.path` so
  `from app.X import Y` works regardless of the hyphenated folder name.

## CI

GitHub Actions runs all tests on every push/PR to `main` or `develop`.
Tests are **not** suppressed with `|| true` — CI fails honestly on test failure.

```yaml
- run: pytest services/book-service/tests/ -v --tb=short
- run: pytest services/member-service/tests/ -v --tb=short
- run: pytest services/lending-service/tests/ -v --tb=short
- run: pytest services/api-gateway/tests/ -v --tb=short
```
