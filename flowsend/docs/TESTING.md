# FlowSend Testing Guide

> Part of [FlowSend](README.md) documentation

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-asyncio | Async test support |
| httpx.AsyncClient | HTTP client for API testing |
| SQLAlchemy 2.0 (async) | Database access in fixtures |
| PostgreSQL 16 | Test database |

## Running Tests

```bash
# All tests (from flowsend/ directory)
make test-backend

# From backend/ directory
pytest -v

# Specific file
pytest tests/test_contacts.py -v

# Single test by name
pytest tests/test_flows.py -v -k "test_activate_flow_with_steps"

# With output (debugging)
pytest -v -s

# With coverage
pytest --cov=app --cov-report=html
```

## Coverage Summary

FlowSend has **151 backend tests**.

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_flows.py` | 24 | Flow CRUD, lifecycle (draft/active/paused), activate with/without steps, pause active/draft, update active rejected, reactivate, executions |
| `test_contacts.py` | 22 | Contact CRUD, bulk import (email + CSV), deduplication, contact lists, pagination, search, tag filter, count |
| `test_campaigns.py` | 21 | Campaign CRUD, scheduling, mock send, send-already-sent rejected, delete-sent rejected, analytics, events, status filter |
| `test_templates.py` | 18 | Template CRUD, minimal create, validation (missing fields, empty name), category filter, pagination, partial update |
| `test_auth.py` | 11 | Register (success, duplicate, short password), login (success, wrong password, nonexistent), refresh, profile, unauthenticated |
| `test_billing.py` | 9 | List plans (public), plan pricing, checkout pro, checkout free fails, duplicate subscription, billing overview, current subscription |
| `test_api_keys.py` | 5 | Create key (raw key returned), list keys (no raw), revoke, auth via API key, invalid key |
| `test_platform_webhooks.py` | -- | Platform event webhook handling |
| `test_health.py` | 1 | Health check returns 200 with service metadata |
| **Total** | **151** | |

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before tests; terminates non-self connections and TRUNCATE CASCADE after each test |
| `db` | function | Raw `AsyncSession` for direct database access |
| `client` | function | Unauthenticated `httpx.AsyncClient` at `http://test` |
| `auth_headers` | function | Dict with `Authorization: Bearer <token>` for a freshly registered user |

### Helper Functions

| Function | Description |
|----------|-------------|
| `register_and_login(client, email?)` | Registers a user and returns auth headers dict |
| `_create_contact(client, headers, email)` | Creates a contact and returns its UUID |

## Test Isolation

FlowSend uses aggressive test isolation:

1. **Table truncation** -- After each test, all tables are truncated with `TRUNCATE ... CASCADE`
2. **Connection termination** -- Before truncation, non-self DB connections are terminated to prevent deadlocks
3. **NullPool** -- SQLAlchemy's `NullPool` prevents connection reuse across tests

## Mock Stripe Mode

All billing tests run in **mock mode**. Leave `STRIPE_SECRET_KEY` empty in `.env` to enable:
- Subscriptions created directly in the database
- No HTTP requests to Stripe
- Faster test execution

## Writing New Tests

### Pattern

All tests use Arrange-Act-Assert with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_my_feature(client: AsyncClient, auth_headers: dict):
    """Test description goes here."""
    # Arrange
    payload = {"name": "Test Item", "value": 42}

    # Act
    response = await client.post("/api/v1/my-endpoint", json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
```

### Naming Convention

- `test_<action>_<expected_outcome>` -- e.g., `test_create_contact_success`
- `test_<action>_<error_case>` -- e.g., `test_create_contact_duplicate_email`
- `test_<action>_<edge_case>` -- e.g., `test_activate_flow_without_steps`

Every test function must have a docstring explaining what it tests.

### Testing Multiple Users

```python
@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient):
    """Verify users can't see each other's data."""
    headers1 = await register_and_login(client, "user1@example.com")
    headers2 = await register_and_login(client, "user2@example.com")

    await client.post("/api/v1/contacts", json={"email": "c@example.com"}, headers=headers1)

    response = await client.get("/api/v1/contacts", headers=headers2)
    assert response.json()["total"] == 0
```

## Debugging

```bash
# Full output
pytest -v -s tests/test_contacts.py

# Last failed only
pytest --lf

# Drop into PDB on failure
pytest --pdb

# SQL query logging (add to test file)
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [README](README.md)*
