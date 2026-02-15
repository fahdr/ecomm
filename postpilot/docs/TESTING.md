# PostPilot Testing Guide

> Part of [PostPilot](README.md) documentation

## Test Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Test Framework | pytest + pytest-asyncio | Async test support for FastAPI |
| HTTP Client | httpx.AsyncClient | In-process ASGI testing (no network) |
| Database | PostgreSQL 16 | Same instance, tables truncated between tests |
| Stripe | Mock mode | `STRIPE_SECRET_KEY` empty -- no real API calls |
| AI Generation | Mock mode | Template-based captions, no real LLM calls |

## Running Tests

```bash
# Run all 157 backend tests
make test-backend

# Verbose output with test names
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_posts.py -v

# Run a single test by name
cd backend && pytest tests/test_queue.py::test_generate_caption_for_queue_item -v

# Run tests matching a keyword
cd backend && pytest -k "calendar" -v

# Show print output
cd backend && pytest -v -s

# Stop on first failure
cd backend && pytest -x

# Run last failed tests only
cd backend && pytest --lf

# Coverage report
cd backend && pytest --cov=app --cov-report=html
```

## Test Coverage (157 tests)

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_queue.py` | 22 | Content queue CRUD, AI caption generation, approve/reject workflow, status transitions, deletion rules, user isolation |
| `test_posts.py` | 20 | Post CRUD, draft vs scheduled, pagination, status/platform filtering, update, delete, scheduling, calendar view, user isolation |
| `test_accounts.py` | 16 | Social account connect (3 platforms), list, disconnect, auto-generated external IDs, validation, user isolation |
| `test_auth.py` | 10 | Registration, duplicate email (409), short password (422), login, wrong password (401), token refresh, profile |
| `test_billing.py` | 9 | Plan listing, pricing, checkout, checkout errors, billing overview, current subscription |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, auth via X-API-Key, invalid key (401) |
| `test_health.py` | 1 | Health check returns status, service name, timestamp |

### By Feature

| Feature | Tests | What's Covered |
|---------|-------|----------------|
| Content Queue | 22 | CRUD, AI captions, approve/reject, state transitions |
| Posts | 20 | CRUD, scheduling, calendar, filtering, isolation |
| Social Accounts | 16 | Connect, list, disconnect, validation |
| Authentication | 10 | Register, login, refresh, profile, errors |
| Billing | 9 | Plans, checkout, subscriptions, overview |
| API Keys | 5 | Create, list, revoke, authentication |
| Health | 1 | Service availability |

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop shared across all tests |
| `setup_db` | function (autouse) | Creates tables before test; terminates other DB connections and truncates all tables after |
| `db` | function | Raw async database session |
| `client` | function | `httpx.AsyncClient` configured against the FastAPI app |
| `auth_headers` | function | Registers a fresh user and returns `{"Authorization": "Bearer <token>"}` |

### Database Isolation

- `setup_db` uses `TRUNCATE CASCADE` on all tables (users, social_accounts, posts, post_metrics, content_queue, subscriptions, api_keys) after each test
- Other DB connections are terminated before truncation to avoid deadlocks
- `get_db` dependency is overridden to use a test session factory with `NullPool`

### Helper: `register_and_login(client, email=None)`

Creates additional users within tests. Returns auth headers dict.

```python
async def test_user_isolation(client, auth_headers):
    user_b_headers = await register_and_login(client)
    # User A creates a post (using auth_headers fixture)
    # User B cannot see it (using user_b_headers)
```

## Mock Services

**Stripe** -- When `STRIPE_SECRET_KEY` is empty, billing service creates subscriptions directly in DB without Stripe API calls. All billing tests work without credentials.

**AI Captions** -- Caption generation uses template-based logic (not real LLM calls). Captions are predictable and testable without API access.

## Writing New Tests

### Guidelines

1. **One behavior per test** -- each test verifies a single thing
2. **Descriptive names** -- `test_create_post_as_draft` not `test_post_1`
3. **AAA pattern** -- Arrange, Act, Assert
4. **Test error cases** -- not just happy paths
5. **Test user isolation** -- verify users cannot access other users' data
6. **Test state transitions** -- verify invalid transitions return 400

### Required Coverage for New Features

1. Happy path (successful creation/update/deletion)
2. Validation errors (422)
3. Authentication errors (401)
4. Authorization / user isolation (404)
5. Plan limit enforcement (403)
6. State transition errors (400)
7. Pagination (if list endpoint)

### Test Template

```python
import pytest
from tests.conftest import register_and_login

@pytest.mark.asyncio
async def test_create_resource(client, auth_headers):
    """Test creating a new resource returns 201 with correct data."""
    resp = await client.post("/api/v1/endpoint", json={"field": "value"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["field"] == "value"

@pytest.mark.asyncio
async def test_user_cannot_access_other_resources(client, auth_headers):
    """Verify cross-user isolation returns 404."""
    resp = await client.post("/api/v1/posts", json={...}, headers=auth_headers)
    post_id = resp.json()["id"]

    user_b = await register_and_login(client)
    resp = await client.get(f"/api/v1/posts/{post_id}", headers=user_b)
    assert resp.status_code == 404
```

## Debugging Tests

```bash
# Verbose with print output
pytest -v -s

# Full diff on assertion failures
pytest -vv

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Run only last failed tests
pytest --lf
```

### Common Failure Patterns

| Symptom | Solution |
|---------|----------|
| `TooManyConnectionsError` | Ensure `setup_db` terminates connections before truncation |
| `ForeignKeyViolationError` | Use `TRUNCATE CASCADE` |
| Tests fail with 401 after first test | Use `auth_headers` fixture (fresh user per test) |
| Tests pass individually but fail together | Ensure no shared state between tests |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [README](README.md)*
