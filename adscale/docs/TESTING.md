# AdScale Testing Guide

> Part of [AdScale](README.md) documentation

Testing infrastructure, coverage, fixtures, and patterns for the AdScale backend.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test framework and runner |
| **pytest-asyncio** | Async test support for FastAPI |
| **httpx.AsyncClient** | HTTP client for API-level testing (no server required) |
| **SQLAlchemy + NullPool** | Database isolation with per-test truncation |
| **PostgreSQL 16** | Same database engine as production |

---

## Running Tests

```bash
# All tests
make test-backend

# Verbose with timing
cd backend && pytest -v --durations=10

# With coverage
cd backend && pytest --cov=app --cov-report=html

# Single file
cd backend && pytest tests/test_campaigns.py -v

# Single test
cd backend && pytest tests/test_campaigns.py::test_create_campaign_success -v
```

---

## Test Coverage

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_auth.py` | 11 | Register, login, refresh, profile, duplicate email (409), invalid credentials (401), short password (422) |
| `test_accounts.py` | 15 | Connect Google/Meta (201), duplicate (409), list with pagination, user isolation, disconnect (204/404/400) |
| `test_campaigns.py` | 20 | Full CRUD, all objectives, lifetime budget, plan limits (403), pagination, user isolation, cascade delete |
| `test_creatives.py` | 16 | Creative CRUD, custom CTA, invalid ad group (400), filter by ad group, AI copy generation, user isolation |
| `test_rules.py` | 20+ | Rule CRUD, all rule types, inactive rules, custom conditions, execute-now, user isolation |
| `test_billing.py` | 9 | Plan listing (3 tiers), pricing details, checkout Pro (201), checkout Free (400), billing overview, subscriptions |
| `test_api_keys.py` | 5 | Create key (raw key returned), list (no raw key), revoke (204), auth via X-API-Key, invalid key (401) |
| `test_health.py` | 1 | Health check returns status, service name, timestamp |
| **Total** | **164** | |

---

## Test File Structure

```
backend/tests/
├── conftest.py          # Shared fixtures and test infrastructure
├── test_auth.py         # Authentication and user management
├── test_accounts.py     # Ad account connection and management
├── test_campaigns.py    # Campaign CRUD and plan limits
├── test_creatives.py    # Creative CRUD and AI copy generation
├── test_rules.py        # Optimization rule CRUD and execution
├── test_billing.py      # Subscription and billing
├── test_api_keys.py     # API key management and authentication
└── test_health.py       # Health check endpoint
```

---

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop shared across all tests |
| `setup_db` | function (autouse) | Creates tables before test, truncates all tables after |
| `db` | function | Raw async database session for direct DB queries |
| `client` | function | `httpx.AsyncClient` configured for the FastAPI app |
| `auth_headers` | function | Pre-registered user with Bearer token headers |

## Helper Functions

| Helper | Location | Purpose |
|--------|----------|---------|
| `register_and_login(client, email)` | conftest.py | Register user, return auth headers dict |
| `_connect_account(client, headers, ...)` | test_accounts.py | Connect a Google/Meta ad account |
| `_create_ad_account(client, headers, ...)` | test_campaigns.py | Create ad account, return UUID |
| `_create_campaign(client, headers, ...)` | test_campaigns.py | Create campaign, return response |
| `_setup_chain(client, headers, ...)` | test_creatives.py | Create full account > campaign > ad group chain |
| `_create_creative(client, headers, ...)` | test_creatives.py | Create ad creative in an ad group |
| `_create_rule(client, headers, ...)` | test_rules.py | Create optimization rule |

---

## Database Isolation

Each test is fully isolated via table truncation:

1. **Tables created** once at session start via `Base.metadata.create_all`
2. **Connections terminated** after each test (prevents deadlocks on FK constraints)
3. **Tables truncated** with `CASCADE` in reverse dependency order:

```
campaign_metrics → ad_creatives → ad_groups → campaigns →
ad_accounts → optimization_rules → api_keys → subscriptions → users
```

> **Important:** Schema-based isolation is used when running alongside other services. The `adscale_test` schema is set via SQLAlchemy `connect` event listener.

---

## Writing Tests

### Naming Convention

| Pattern | Example |
|---------|---------|
| `test_<action>_<entity>_<scenario>` | `test_create_campaign_success` |
| `test_<action>_<entity>_<error>` | `test_create_campaign_plan_limit` |
| `test_<entity>_<property>` | `test_campaign_platform_denormalized` |

### Standard Pattern

```python
@pytest.mark.asyncio
async def test_create_campaign_success(client, auth_headers):
    """Test: Create a campaign successfully returns 201 with campaign data."""
    # Setup
    account_id = await _create_ad_account(client, auth_headers)

    # Execute
    payload = {
        "ad_account_id": account_id,
        "name": "Spring Sale",
        "objective": "sales",
        "budget_daily": 50.0,
        "status": "draft"
    }
    resp = await client.post("/api/v1/campaigns", json=payload, headers=auth_headers)

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Spring Sale"
    assert data["platform"] == "google"  # Denormalized from ad account
```

### Best Practices

1. **Use helper functions** for setup -- avoid duplicating account/campaign creation logic
2. **One behavior per test** -- avoid monolithic tests that verify multiple things
3. **Assert status code first** before calling `.json()` on the response
4. **Descriptive names** -- `test_create_campaign_success` not `test_campaign1`
5. **Test edge cases** -- empty lists, invalid UUIDs, plan limits, user isolation, cascade deletes, null/optional fields
6. **Clean up is automatic** -- `setup_db` truncates; only close manually-created DB connections

---

## Debugging

```bash
pytest tests/test_campaigns.py -v        # Verbose output
pytest tests/test_campaigns.py -s        # Show print statements
pytest tests/test_campaigns.py --pdb     # Drop into debugger on failure
```

---

## CI/CD

Tests run on every push and pull request. The CI pipeline uses:

```bash
make test-backend
```

PostgreSQL 16 and Redis 7 are provisioned as service containers. All 164 tests must pass before merging.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
