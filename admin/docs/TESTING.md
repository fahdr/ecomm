# Testing Guide

> Part of [Admin Dashboard](README.md) documentation

Test stack, running tests, coverage reports, and test patterns for the Super Admin Dashboard.

## Test Stack

**Backend (pytest):**
- pytest 7.4+
- pytest-asyncio (async test support)
- httpx (AsyncClient for API testing)
- SQLAlchemy 2.0 (async ORM)
- asyncpg (PostgreSQL async driver)

**Test Database:**
- PostgreSQL 13+ (shared database)
- Schema isolation: `admin_test` schema
- Per-test table truncation for data isolation

## Running Tests

### Backend Tests

```bash
cd admin/backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py

# Run tests matching a pattern
pytest -k "test_login"

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

### Dashboard Tests

**Not yet implemented.** The dashboard currently has no automated tests. Future plans:
- Vitest for unit tests
- Playwright for E2E tests

## Test Coverage

**Total: 34 tests across 4 test modules**

| Test File                  | Lines | Tests | Coverage Areas                                    |
|----------------------------|-------|-------|---------------------------------------------------|
| `test_auth.py`             | 201   | 7     | Setup, login, profile, token validation           |
| `test_health_monitor.py`   | 253   | 9     | Service pings, health history, snapshots          |
| `test_llm_proxy.py`        | 344   | 12    | Provider CRUD, usage endpoints, proxy errors      |
| `test_services_overview.py`| 195   | 6     | Service listing, port extraction, health merging  |

### Test Breakdown by Module

**test_auth.py (7 tests):**
- `test_setup_creates_first_admin` — POST /auth/setup creates super_admin
- `test_setup_fails_when_admin_exists` — Setup returns 409 after first admin
- `test_login_success` — POST /auth/login returns JWT token
- `test_login_invalid_credentials` — Login returns 401 for wrong password
- `test_login_inactive_admin` — Login returns 401 for deactivated admin
- `test_get_me_success` — GET /auth/me returns admin profile
- `test_get_me_invalid_token` — GET /auth/me returns 401 for bad token

**test_health_monitor.py (9 tests):**
- `test_check_all_services_success` — Health checks ping all services
- `test_check_all_services_creates_snapshots` — Snapshots persisted to DB
- `test_check_all_services_healthy_status` — HTTP 200 = healthy
- `test_check_all_services_degraded_status` — Non-200 = degraded
- `test_check_all_services_down_status` — Timeout = down
- `test_health_history_default` — History returns last 50 snapshots
- `test_health_history_filtered` — History filters by service_name
- `test_health_history_limit` — History respects limit parameter
- `test_health_history_order` — History ordered by checked_at desc

**test_llm_proxy.py (12 tests):**
- `test_list_providers` — GET /llm/providers proxies to gateway
- `test_create_provider` — POST /llm/providers proxies to gateway
- `test_update_provider` — PATCH /llm/providers/:id proxies to gateway
- `test_delete_provider` — DELETE /llm/providers/:id proxies to gateway
- `test_usage_summary` — GET /llm/usage/summary proxies to gateway
- `test_usage_by_provider` — GET /llm/usage/by-provider proxies to gateway
- `test_usage_by_service` — GET /llm/usage/by-service proxies to gateway
- `test_proxy_gateway_error` — 500 from gateway returns 500
- `test_proxy_gateway_timeout` — Timeout returns 504
- `test_proxy_gateway_connect_error` — Connection error returns 502
- `test_proxy_authentication` — All endpoints require admin JWT
- `test_proxy_headers_include_service_key` — X-Service-Key header set

**test_services_overview.py (6 tests):**
- `test_list_services_no_snapshots` — Returns all services with unknown status
- `test_list_services_with_snapshots` — Merges latest snapshot per service
- `test_list_services_count` — Returns all 9 configured services
- `test_extract_port_from_url` — Port extraction helper works
- `test_services_require_auth` — Endpoint requires JWT
- `test_services_merge_api_and_defaults` — API data merged with defaults

## Test Fixtures

### Session-Scoped Fixtures

**`create_tables` (session-scoped, autouse):**
- Creates `admin_test` schema once per session
- Terminates stale connections from prior runs
- Creates all admin tables with `Base.metadata.create_all()`
- Overrides `get_db` dependency to use test session factory
- Disposes engine on teardown

**`event_loop` (session-scoped):**
- Provides a single event loop for all async tests

### Function-Scoped Fixtures

**`truncate_tables` (autouse):**
- Truncates all tables before each test for data isolation
- Uses `TRUNCATE TABLE ... CASCADE` to clear related data
- Disposes app engine to prevent connection conflicts

**`db` (function-scoped):**
- Yields an async database session for direct model operations
- Scoped to the test function lifecycle

**`client` (function-scoped):**
- Yields an httpx `AsyncClient` wired to the FastAPI app
- Base URL: `http://test`
- Used for API endpoint testing

**`auth_headers` (function-scoped):**
- Creates a super_admin user
- Generates a JWT token for the admin
- Returns `{"Authorization": "Bearer <token>"}` dict
- Used to authenticate API requests in tests

### Helper Functions

**`create_admin(db, email, password, role, is_active)`:**
- Creates an `AdminUser` in the database
- Hashes the password with bcrypt
- Flushes, refreshes, and commits
- Returns the created `AdminUser` ORM object

## Schema Isolation Pattern

**Critical for avoiding test conflicts in the shared PostgreSQL database.**

### How It Works

1. **Schema creation (session-scoped):**
   - Terminates stale connections to `admin_test` schema
   - Drops and recreates `admin_test` schema via raw asyncpg
   - Creates tables with SQLAlchemy `Base.metadata.create_all()`

2. **Search path configuration:**
   - Engine has a `connect` event listener
   - Every new connection runs `SET search_path TO admin_test`
   - SQLAlchemy queries automatically target the test schema

3. **Table truncation (per-test):**
   - Uses `TRUNCATE TABLE ... CASCADE` on all tables
   - Prevents test data from leaking between tests
   - Much faster than dropping/recreating tables

### Why Schema Isolation?

- Multiple services share the same PostgreSQL database
- Without schemas, `pg_terminate_backend` kills other services' connections
- Schema-prefixed tables (e.g., `admin_test.admin_users`) are isolated
- Pattern matches other ecomm services (trendscout, contentforge, etc.)

## Test Patterns

### Testing Authenticated Endpoints

```python
async def test_endpoint_requires_auth(client):
    """Verify endpoint returns 401 without JWT."""
    resp = await client.get("/api/v1/admin/services")
    assert resp.status_code == 401

async def test_endpoint_success(client, auth_headers):
    """Verify endpoint returns 200 with valid JWT."""
    resp = await client.get("/api/v1/admin/services", headers=auth_headers)
    assert resp.status_code == 200
```

### Testing Database Operations

```python
async def test_create_admin(db):
    """Verify admin user creation."""
    admin = await create_admin(db, email="test@example.com")
    assert admin.email == "test@example.com"
    assert admin.role == "super_admin"
    assert admin.is_active is True

    # Verify persisted
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == "test@example.com")
    )
    fetched = result.scalar_one()
    assert fetched.id == admin.id
```

### Testing Proxy Endpoints (Mocking httpx)

```python
from unittest.mock import AsyncMock, patch

async def test_proxy_endpoint(client, auth_headers):
    """Verify LLM Gateway proxy."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "uuid", "name": "openai"}]

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        resp = await client.get("/api/v1/admin/llm/providers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "openai"
```

### Testing Health Monitoring

```python
async def test_health_check_creates_snapshot(client, auth_headers, db):
    """Verify health snapshot persistence."""
    # Mock httpx to return healthy status
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "healthy"}

        resp = await client.get("/api/v1/admin/health/services", headers=auth_headers)
        assert resp.status_code == 200

    # Verify snapshot was created
    result = await db.execute(select(ServiceHealthSnapshot))
    snapshots = result.scalars().all()
    assert len(snapshots) > 0
```

## Common Test Failures

**`pg_terminate_backend` kills other services:**
- Ensure you're using schema isolation (conftest.py)
- Check that the terminate query filters by schema: `WHERE query LIKE '%admin_test%'`

**Tests fail with "relation does not exist":**
- Verify `search_path` is set in the engine's connect event
- Check that `create_tables` fixture ran successfully
- Try `pytest -v` to see detailed setup logs

**JWT token invalid in tests:**
- Ensure `auth_headers` fixture is used
- Verify `create_admin` helper is creating the user before token generation
- Check that `settings.admin_secret_key` is consistent

**Health check tests timeout:**
- Mock httpx calls to avoid actual network requests
- Use `patch("httpx.AsyncClient.get")` to return fake responses

**Snapshot isolation failures:**
- Ensure `truncate_tables` fixture is running (autouse=True)
- Check that the fixture disposes the app engine before truncating

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [QA Engineer Guide](QA_ENGINEER.md)*
