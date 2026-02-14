# TrendScout Testing Guide

> Part of [TrendScout](README.md) documentation

This guide covers the test stack, running tests, test coverage, fixtures, and writing new tests for the TrendScout service.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and framework |
| pytest-asyncio | Async test support for FastAPI |
| httpx (AsyncClient) | HTTP client for API testing |
| SQLAlchemy (async) | Direct database operations in test helpers |
| Playwright | E2E browser testing (planned) |

---

## Running Tests

```bash
# Run all backend tests
cd trendscout/backend
pytest

# Run with verbose output (see individual test names)
pytest -v

# Run a specific test file
pytest tests/test_research.py
pytest tests/test_watchlist.py
pytest tests/test_sources.py
pytest tests/test_auth.py
pytest tests/test_billing.py
pytest tests/test_api_keys.py
pytest tests/test_health.py

# Run a single test by name
pytest tests/test_research.py::test_create_research_run -v

# Run tests with coverage report
pytest --cov=app tests/

# Run tests matching a keyword
pytest -k "watchlist" -v
```

---

## Verify Dashboard Build

```bash
cd trendscout/dashboard
npm run build
```

---

## Verify Landing Page Build

```bash
cd trendscout/landing
npm run build
```

---

## Current Test Coverage

| Test File | Test Count | Coverage Area |
|-----------|-----------|---------------|
| `tests/test_auth.py` | 10 | Registration, login, token refresh, profile, duplicate email, invalid credentials, unauthenticated access |
| `tests/test_billing.py` | 9 | Plan listing, checkout session creation, free plan rejection, duplicate subscription, billing overview, current subscription |
| `tests/test_research.py` | 21 | Research run CRUD (create, list, get detail, delete), pagination, user isolation, score_config override, empty keywords validation, result detail, unauthenticated/wrong-user access |
| `tests/test_watchlist.py` | 24 | Add to watchlist (with notes, duplicate rejection, nonexistent result), list with status filter and pagination, update status/notes, delete, user isolation, re-add after delete |
| `tests/test_sources.py` | 22 | Source config CRUD (all 4 valid types, invalid type rejection), credential redaction verification, settings/credentials/active-toggle update, list ordering, user isolation, delete |
| `tests/test_api_keys.py` | 5 | Key creation (raw key returned), listing (no raw key), revocation (key deactivated), auth via X-API-Key header, invalid key rejection |
| `tests/test_health.py` | 1 | Health check endpoint returns 200 with service metadata |
| `tests/test_platform_webhooks.py` | -- | Platform event webhook handling |
| **Total** | **158** | **Full feature coverage** |

---

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures (client, db, auth_headers)
├── test_auth.py             # Authentication endpoint tests
├── test_billing.py          # Billing & subscription tests
├── test_research.py         # Research run CRUD + result detail tests
├── test_watchlist.py        # Watchlist CRUD + plan limit tests
├── test_sources.py          # Source configuration CRUD tests
├── test_api_keys.py         # API key management + key auth tests
└── test_health.py           # Health check endpoint test
```

---

## Fixtures (conftest.py)

### `client` (AsyncClient)

An httpx `AsyncClient` wired to the FastAPI app. Use for all HTTP requests in tests.

**Usage**:
```python
async def test_example(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

---

### `db` (AsyncSession)

A raw database session for direct model manipulation (e.g., inserting `ResearchResult` records that are normally created by Celery tasks).

**Usage**:
```python
from app.models.research import ResearchResult

async def test_example(db):
    result = ResearchResult(
        run_id=run_id,
        source="aliexpress",
        product_title="Test Product",
        score=85.0
    )
    db.add(result)
    await db.commit()
```

---

### `auth_headers` (dict)

Registers a new user and returns `{"Authorization": "Bearer <token>"}`. Each test gets a fresh user.

**Usage**:
```python
async def test_example(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
```

---

### `register_and_login(client, email?)` (helper function)

Registers a user with the given (or random) email and returns auth headers. Use when you need multiple users in a test (e.g., for user isolation checks).

**Usage**:
```python
async def test_user_isolation(client, auth_headers):
    # First user (from auth_headers fixture)
    # ...

    # Second user
    other_headers = await register_and_login(client, "other@example.com")
    # ...
```

---

### `setup_db` (autouse fixture)

Creates all tables before each test and truncates all tables after each test with `CASCADE`. Terminates all non-self database connections before truncation to prevent deadlocks.

This fixture runs automatically for every test (no need to specify it in test parameters).

---

## Writing Tests

### Basic Patterns

**Simple Endpoint Test**:
```python
async def test_feature(client, auth_headers):
    resp = await client.post("/api/v1/endpoint", headers=auth_headers, json={...})
    assert resp.status_code == 201
    assert resp.json()["field"] == "expected"
```

**User Isolation**:
```python
async def test_isolation(client, auth_headers):
    resp = await client.post("/api/v1/resource", headers=auth_headers, json={...})
    resource_id = resp.json()["id"]

    other_headers = await register_and_login(client, "other@example.com")
    resp = await client.get(f"/api/v1/resource/{resource_id}", headers=other_headers)
    assert resp.status_code == 404  # Not 403
```

**Plan Limits**:
```python
async def test_limit(client, auth_headers):
    for _ in range(5): # At limit
        resp = await client.post("/api/v1/runs", headers=auth_headers, json={...})
        assert resp.status_code == 201

    resp = await client.post("/api/v1/runs", headers=auth_headers, json={...})
    assert resp.status_code == 403  # Exceeded
```

**Direct DB Access**:
```python
async def test_with_db(client, db, auth_headers):
    resp = await client.post("/api/v1/runs", headers=auth_headers, json={...})
    result = ResearchResult(run_id=resp.json()["id"], source="aliexpress", score=85.0)
    db.add(result)
    await db.commit()
```

---

## Test Isolation & Mock Mode

**Schema Isolation**: All tests run in the `trendscout_test` PostgreSQL schema to avoid conflicts with other services.

**Mock Mode**: No external API calls are made during testing:
- **Stripe**: Mock checkout/portal URLs, test webhook fixtures
- **AI Analysis**: Deterministic mock based on product title hash
- **Data Sources**: Mock generators for AliExpress, TikTok, Google Trends, Reddit

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
