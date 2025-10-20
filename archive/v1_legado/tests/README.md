# 🧪 Tests Directory

This directory contains test files for the Sistema Aprender project.

## Structure

```
tests/
├── legacy/           # Historical test files from development
├── unit/            # Unit tests (organized by module)
├── integration/     # Integration tests
├── e2e/            # End-to-end tests
└── fixtures/       # Test data fixtures
```

## Legacy Tests (`legacy/`)

Contains test files that were created during the initial development phase:
- Various `test_*.py` files covering different aspects of the system
- These were moved here during repository cleanup to maintain history
- May contain useful test cases that should be integrated into the main test suite

## Main Test Structure (To be organized)

The main test suite should be organized as:

### Unit Tests (`unit/`)
- `test_models.py` - Model tests
- `test_views.py` - View tests  
- `test_forms.py` - Form tests
- `test_services.py` - Service layer tests

### Integration Tests (`integration/`)
- `test_google_calendar.py` - Google Calendar integration
- `test_workflows.py` - End-to-end workflow tests
- `test_authentication.py` - Authentication flow tests

### E2E Tests (`e2e/`)
- `test_user_flows.py` - Complete user journey tests
- `conftest.py` - Playwright configuration

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# E2E tests
make test-e2e

# With coverage
make test-coverage
```

## Test Guidelines

1. **Naming**: Test files should start with `test_`
2. **Organization**: Group related tests in the same file
3. **Coverage**: Aim for >80% test coverage
4. **Documentation**: Add docstrings to test classes and complex test methods
5. **Fixtures**: Use fixtures for common test data

## Legacy Migration

TODO: Review legacy test files and:
1. Extract useful test cases
2. Refactor into the organized structure
3. Remove duplicate or obsolete tests
4. Update to current Django testing patterns

---
*Tests directory organized during repository cleanup - Phase 4*
*Date: 2025-09-11*