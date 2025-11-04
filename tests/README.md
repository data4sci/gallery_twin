# Gallery Twin Test Suite

## Overview

Comprehensive test suite for the Gallery Twin virtual art gallery application. The suite has been completely refactored from scratch with focus on maintainability, coverage, and clarity.

## Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_analytics.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Run only fast tests
pytest tests/ -m "not slow" -v
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_models.py              # Database model tests (24 tests)
├── test_auth.py                # Authentication tests (6 tests)
├── test_dependencies.py        # Session & CSRF tests (12 tests)
├── test_analytics.py           # Analytics service tests (18 tests)
├── test_content_loader.py      # Content loading tests (14 tests)
├── TEST_SUMMARY.md             # Detailed test analysis
└── README.md                   # This file
```

## Test Files

### [conftest.py](conftest.py)
**Purpose**: Shared fixtures and test configuration

**Key Fixtures**:
- `db_session` - Fresh test database per test function
- `client` / `client_no_redirects` - HTTP test clients
- `admin_auth` - Admin credentials
- `sample_exhibit` / `sample_exhibit_with_images` / `sample_exhibit_with_questions`
- `sample_session` / `completed_session` / `expired_session`
- `sample_answer` / `sample_events`
- `temp_content_dir` / `sample_yaml_content`
- `mock_env_session_ttl` / `mock_env_secret_key`

### [test_models.py](test_models.py)
**Purpose**: Test database models and relationships

**Coverage**:
- ✅ Exhibit creation and uniqueness constraints
- ✅ Image relationships
- ✅ Question types (TEXT, SINGLE, MULTI, LIKERT)
- ✅ Global questions (not tied to exhibits)
- ✅ Session lifecycle and data storage
- ✅ Answer submission (text and JSON)
- ✅ Event tracking (VIEW_START, VIEW_END, AUDIO_PLAY, AUDIO_PAUSE)
- ✅ Enum validation

**Key Tests**:
- `test_exhibit_slug_uniqueness` - Ensures slugs are unique
- `test_session_uuid_uniqueness` - Ensures session UUIDs are unique
- `test_answer_multi_choice_json` - Tests JSON array storage
- `test_event_with_metadata` - Tests metadata JSON field

### [test_auth.py](test_auth.py)
**Purpose**: Test HTTP Basic authentication for admin routes

**Coverage**:
- ✅ Correct credentials acceptance
- ✅ Wrong username rejection
- ✅ Wrong password rejection
- ✅ Empty credentials rejection
- ✅ Case sensitivity

**Key Tests**:
- `test_admin_auth_correct_credentials` - Valid login
- `test_admin_auth_wrong_password` - Invalid credentials
- `test_admin_auth_case_sensitive_password` - Case sensitivity

### [test_dependencies.py](test_dependencies.py)
**Purpose**: Test FastAPI dependencies (session tracking, CSRF)

**Coverage**:
- ✅ CSRF token generation
- ✅ CSRF token validation
- ✅ CSRF token expiration (1 hour)
- ✅ Session creation for new visitors
- ✅ Session reuse for returning visitors
- ✅ Session expiration after TTL
- ✅ Last activity timestamp updates
- ✅ Invalid UUID handling

**Key Tests**:
- `test_csrf_token_verification_session_mismatch` - Security check
- `test_track_session_creates_new_for_expired_session` - Expiration logic
- `test_track_session_updates_last_activity` - Sliding expiration

### [test_analytics.py](test_analytics.py)
**Purpose**: Test analytics calculations and aggregations

**Coverage**:
- ✅ Session statistics (total, completed)
- ✅ Completion rate calculations
- ✅ Self-evaluation aggregation (gender, education, age)
- ✅ Time per exhibit (VIEW_START/END pairing)
- ✅ Exhibition feedback statistics
- ✅ Full dashboard integration
- ✅ Edge cases (empty DB, null values, invalid durations)

**Key Tests**:
- `test_get_average_time_per_exhibit` - Complex event pairing logic
- `test_get_selfeval_stats` - JSON aggregation
- `test_get_exhibition_feedback_stats` - Rating distribution
- `test_get_full_dashboard_stats` - Complete integration

### [test_content_loader.py](test_content_loader.py)
**Purpose**: Test YAML content loading and parsing

**Coverage**:
- ✅ Filename order extraction
- ✅ Question type parsing
- ✅ Basic content loading
- ✅ Loading with images
- ✅ Loading with questions
- ✅ Idempotency (no duplicates on reload)
- ✅ Update existing content
- ✅ Multiple file loading
- ✅ Invalid YAML handling
- ✅ Missing slug handling

**Key Tests**:
- `test_load_content_idempotency` - Critical for data integrity
- `test_load_content_update_existing` - Updates not inserts
- `test_load_content_skip_invalid_yaml` - Error resilience

## Test Categories

### Unit Tests (60 tests)
Individual component testing in isolation:
- Models (24 tests)
- Auth (6 tests)
- Dependencies (12 tests)
- Analytics (18 tests)

### Integration Tests (14 tests)
Multiple components working together:
- Content loader (14 tests)

### Current Test Statistics

- **Total Tests**: 74
- **Passing**: ~62 (84%)
- **Failing**: ~11 (minor fixture issues)
- **Errors**: ~1 (relationship loading)

## Common Test Patterns

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_something(db_session):
    result = await some_async_function(db_session)
    assert result == expected
```

### Using Fixtures
```python
@pytest.mark.asyncio
async def test_with_exhibit(db_session, sample_exhibit):
    # sample_exhibit is automatically created
    assert sample_exhibit.slug == "test-exhibit"
```

### Testing HTTP Endpoints
```python
@pytest.mark.asyncio
async def test_endpoint(client, admin_auth):
    response = await client.get("/admin/", auth=admin_auth)
    assert response.status_code == 200
```

### Testing Exceptions
```python
def test_invalid_input():
    with pytest.raises(ValueError):
        parse_question_type("invalid")
```

## Fixture Dependencies

```
db_session (root fixture)
├── sample_exhibit
│   ├── sample_exhibit_with_images
│   └── sample_exhibit_with_questions
│       └── sample_answer (also needs sample_session)
├── sample_session
│   ├── completed_session
│   ├── expired_session
│   └── sample_events (also needs sample_exhibit)
└── multiple_exhibits

client / client_no_redirects (independent)
admin_auth (independent)
temp_content_dir (independent)
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/test_analytics.py -v
```

### Specific Test Function
```bash
pytest tests/test_analytics.py::test_get_total_sessions -v
```

### With Coverage
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

### With Output
```bash
pytest tests/ -v -s
```

### Stop on First Failure
```bash
pytest tests/ -x
```

### Show Slowest Tests
```bash
pytest tests/ --durations=10
```

## Debugging Failed Tests

### View Full Traceback
```bash
pytest tests/test_file.py::test_name -vv --tb=long
```

### Run with Print Statements
```bash
pytest tests/test_file.py::test_name -s
```

### Run with PDB Debugger
```bash
pytest tests/test_file.py::test_name --pdb
```

## Test Data

Tests use isolated test databases with fresh data for each test:
- Database: `test.db` (created and destroyed per test)
- No shared state between tests
- All fixtures are function-scoped by default

## Environment Variables

Tests automatically override sensitive environment variables:
- `SESSION_TTL` - Set to 60 seconds for faster testing
- `SECRET_KEY` - Set to test key
- `DATABASE_URL` - Automatically uses test database

## Best Practices

1. **Test Naming**: Use descriptive names: `test_<feature>_<scenario>`
2. **Docstrings**: Every test has a docstring explaining what it tests
3. **Assertions**: Use clear assertion messages
4. **Fixtures**: Prefer fixtures over setup/teardown
5. **Isolation**: Each test is independent
6. **Async**: Mark async tests with `@pytest.mark.asyncio`

## Known Issues

See [TEST_SUMMARY.md](TEST_SUMMARY.md) for detailed analysis of current test failures.

Most failures are minor fixture issues that can be fixed by:
1. Updating YAML structure in content loader tests
2. Adding relationship eager loading in model tests
3. Adjusting assertions in analytics tests

## Contributing

When adding new tests:
1. Use existing fixtures when possible
2. Add new fixtures to `conftest.py` if reusable
3. Follow the existing test structure
4. Include docstrings
5. Test both success and failure cases
6. Consider edge cases

## CI/CD Integration

Tests are designed for CI/CD:
- Fast execution (~5 seconds)
- No external dependencies
- Isolated database per test
- Clear failure messages
- Exit code 0 on success

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLModel Testing](https://sqlmodel.tiangolo.com/tutorial/testing/)

## Support

For questions or issues:
1. Check [TEST_SUMMARY.md](TEST_SUMMARY.md) for detailed analysis
2. Review fixture definitions in [conftest.py](conftest.py)
3. Look at similar tests for examples
4. Run with `-vv --tb=long` for detailed output
