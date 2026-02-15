# RankPilot Testing Guide

> Part of [RankPilot](README.md) documentation

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and framework |
| **pytest-asyncio** | Async test support for FastAPI + SQLAlchemy |
| **httpx.AsyncClient** | HTTP client for API integration tests |
| **SQLAlchemy 2.0 (async)** | Database ORM with NullPool for test isolation |
| **PostgreSQL 16** | Test database (same instance, tables truncated between tests) |

## Running Tests

```bash
# Run all 165 backend tests
make test-backend

# Or directly with pytest
pytest backend/tests

# Verbose output
pytest backend/tests -v

# Run a single test file
pytest backend/tests/test_sites.py -v

# Run a specific test by name
pytest backend/tests/test_blog.py::test_create_blog_post_basic -v

# Run tests matching a keyword pattern
pytest backend/tests -k "keyword" -v

# Show print output
pytest backend/tests -v -s

# Stop on first failure
pytest backend/tests -x

# Run last failed tests only
pytest backend/tests --lf
```

## Test Coverage

### Summary (165 tests)

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_health.py` | 1 | Health check endpoint |
| `test_auth.py` | 11 | Registration, login, refresh tokens, profile, duplicates |
| `test_sites.py` | 20 | Site CRUD, pagination, domain verification, cross-user isolation |
| `test_blog.py` | 25 | Blog post CRUD, AI generation, content/keywords, status transitions |
| `test_keywords.py` | 16 | Keyword add/list/delete, duplicates, rank refresh, pagination |
| `test_audits.py` | 15 | Audit execution, score validation, history, pagination |
| `test_billing.py` | 10 | Plan listing, checkout, overview, subscription lifecycle |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, API key authentication |

### By Feature

| Feature | Tests | What's Covered |
|---------|-------|----------------|
| Authentication | 11 | Register, login, refresh, profile, errors |
| Sites | 20 | CRUD, verification, pagination, isolation |
| Blog Posts | 25 | CRUD, AI generation, plan limits, status |
| Keywords | 16 | CRUD, duplicates, rank refresh, limits |
| SEO Audits | 15 | Execution, scoring, history |
| Billing | 10 | Plans, checkout, subscriptions |
| API Keys | 5 | Create, list, revoke, authentication |
| Health | 1 | Service availability |

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `setup_db` | function (autouse) | Creates tables before each test; terminates other DB connections and truncates all tables after |
| `client` | function | `httpx.AsyncClient` configured for the FastAPI app |
| `db` | function | Raw `AsyncSession` for direct database operations |
| `auth_headers` | function | Registers a test user with unique email and returns `{"Authorization": "Bearer <token>"}` |

### Dependency Override

The test suite overrides `get_db` to use a test session factory with `NullPool`, ensuring each test gets an isolated database session.

### Helper: `register_and_login(client, email=None)`

Creates additional users within tests. Registers with a random email and returns auth headers.

```python
async def test_cross_user_isolation(client, auth_headers):
    # User A creates resource (from fixture)
    resp_a = await client.post("/api/v1/sites", headers=auth_headers, json={"domain": "example.com"})

    # User B (manual registration)
    user_b_headers = await register_and_login(client)

    # User B cannot access User A's site
    resp = await client.get(f"/api/v1/sites/{resp_a.json()['id']}", headers=user_b_headers)
    assert resp.status_code == 404
```

## Writing New Tests

### Guidelines

1. **One behavior per test** -- each test verifies a single thing
2. **Descriptive names** -- `test_create_site_with_duplicate_domain` not `test_site_1`
3. **Docstrings** -- explain what the test verifies
4. **AAA pattern** -- Arrange, Act, Assert
5. **Test error cases** -- not just happy paths
6. **Test cross-user isolation** -- verify users cannot access other users' data

### Adding Tests for New Features

1. Create `backend/tests/test_<feature>.py`
2. Import fixtures from `conftest.py`
3. Cover: happy path, validation (422), auth (401), authorization (404), plan limits (403), duplicates (400), pagination
4. Run: `pytest backend/tests/test_<feature>.py -v`

### Test Template

```python
import pytest
from tests.conftest import register_and_login

@pytest.mark.asyncio
async def test_create_resource(client, auth_headers):
    """Test creating a new resource returns 201 with correct data."""
    resp = await client.post("/api/v1/resources", headers=auth_headers, json={"field": "value"})
    assert resp.status_code == 201
    assert resp.json()["field"] == "value"

@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    """Test that unauthenticated requests return 401."""
    resp = await client.get("/api/v1/resources")
    assert resp.status_code == 401
```

## Debugging Tests

```bash
# Verbose with print output and local variables
pytest backend/tests/test_sites.py -v -s -l

# Stop on first failure
pytest backend/tests -x

# Run only last failed tests
pytest backend/tests --lf

# Inspect database state in tests using the `db` fixture
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
