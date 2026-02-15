# Testing

> Part of [SpyDrop](README.md) documentation

This guide covers SpyDrop's test infrastructure, how to run tests, test coverage, and how to write new tests.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and assertions |
| pytest-asyncio | Async test support for FastAPI endpoints |
| httpx `AsyncClient` | In-process HTTP client (no server needed) |
| SQLAlchemy 2.0 async | Direct database access for seeding test data |
| PostgreSQL 16 | Real database (not SQLite) for production-accurate testing |

---

## Running Tests

### All Backend Tests (156 tests)

```bash
# From /workspaces/ecomm/spydrop/
make test-backend

# Or directly:
cd /workspaces/ecomm/spydrop/backend
pytest -v
```

### Run a Specific Test File

```bash
cd /workspaces/ecomm/spydrop/backend
pytest tests/test_competitors.py -v
pytest tests/test_products.py -v
pytest tests/test_auth.py -v
pytest tests/test_billing.py -v
pytest tests/test_api_keys.py -v
pytest tests/test_health.py -v
```

### Run a Single Test

```bash
cd /workspaces/ecomm/spydrop/backend
pytest tests/test_competitors.py::test_create_competitor_plan_limit_free_tier -v
```

### Run with Coverage Report

```bash
cd /workspaces/ecomm/spydrop/backend
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Coverage Table

| Test File | Test Count | Coverage Areas |
|-----------|-----------|----------------|
| `test_auth.py` | 11 | Registration (success, duplicate email, short password), login (success, wrong password, nonexistent user), token refresh (valid, invalid), profile retrieval (authenticated, unauthenticated) |
| `test_competitors.py` | 17 | Create (success, default platform, missing name/url/empty name, unauthenticated, plan limit), list (empty, with data, pagination, user isolation), get single (success, not found, invalid ID, wrong user), update (name, status, multiple fields, not found, wrong user), delete (success, not found, wrong user, reduces count), competitor products (empty, invalid ID) |
| `test_products.py` | 12 | List all (empty, after competitor, unauthenticated, pagination params, invalid page/per_page, sort_by, status filter, user isolation), product detail (not found, invalid ID, unauthenticated), seeded data (list with products, detail with price history, wrong user, status filter active/removed, sort by price) |
| `test_billing.py` | 9 | List plans (returns 3 tiers, has pricing), checkout (pro plan, free plan fails, duplicate subscription fails), billing overview (free plan, after subscribe), current subscription (none, after subscribe) |
| `test_api_keys.py` | 5 | Create key (returns raw key), list keys (no raw key exposed), revoke key (marks inactive), auth via API key (X-API-Key header), invalid API key (returns 401) |
| `test_health.py` | 1 | Health check returns 200 with service name, status "ok", and timestamp |
| `test_platform_webhooks.py` | -- | Platform event webhook handling |
| **Total** | **156** | |

---

## Test Structure

### Fixtures (from `conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single asyncio event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before each test, truncates all with CASCADE after |
| `db` | function | Async SQLAlchemy session for direct database operations |
| `client` | function | httpx `AsyncClient` configured for the FastAPI app |
| `auth_headers` | function | Pre-registered user with `Authorization: Bearer <token>` headers |

### Helper Functions

| Function | Location | Description |
|----------|----------|-------------|
| `register_and_login(client, email?)` | `conftest.py` | Registers a user and returns auth headers dict |
| `create_competitor_via_api(client, headers, name?, url?, platform?)` | `test_competitors.py` | Creates a competitor via POST and returns response JSON |
| `seed_competitor_with_products(db, user_id, name?, count?, status?)` | `test_products.py` | Seeds a competitor with products directly in the database |

---

## Key Testing Patterns

### 1. User Isolation

Tests create multiple users and verify that resources are scoped to each user. Accessing another user's resource returns 404 (not 403).

**Example:**
```python
async def test_get_competitor_wrong_user(client: AsyncClient, db: AsyncSession):
    # User A creates competitor
    headers_a = await register_and_login(client, "user_a@example.com")
    comp = await create_competitor_via_api(client, headers_a)

    # User B tries to access
    headers_b = await register_and_login(client, "user_b@example.com")
    resp = await client.get(f"/api/v1/competitors/{comp['id']}", headers=headers_b)

    assert resp.status_code == 404  # Not 403, to prevent enumeration
```

### 2. Plan Limit Enforcement

Tests create resources up to the free-tier limit (3 competitors) and verify the next creation returns 403.

**Example:**
```python
async def test_create_competitor_plan_limit_free_tier(client: AsyncClient):
    headers = await register_and_login(client, "user@example.com")

    # Create 3 competitors (free tier limit)
    for i in range(3):
        resp = await client.post("/api/v1/competitors/", json={...}, headers=headers)
        assert resp.status_code == 201

    # 4th competitor should fail
    resp = await client.post("/api/v1/competitors/", json={...}, headers=headers)
    assert resp.status_code == 403
    assert "plan limit" in resp.json()["detail"].lower()
```

### 3. Database Seeding

For complex test scenarios (products with price history), data is seeded directly via the SQLAlchemy session rather than through the API.

**Example:**
```python
async def seed_competitor_with_products(db: AsyncSession, user_id: UUID, count: int = 5):
    competitor = Competitor(
        user_id=user_id,
        name="Test Competitor",
        url="https://test.com",
        platform="shopify",
    )
    db.add(competitor)
    await db.flush()

    for i in range(count):
        product = CompetitorProduct(
            competitor_id=competitor.id,
            title=f"Product {i+1}",
            price=10.0 + i,
            price_history=[
                {"date": "2026-02-10T10:00:00Z", "price": 12.0 + i},
                {"date": "2026-02-12T10:00:00Z", "price": 10.0 + i},
            ],
        )
        db.add(product)

    await db.commit()
    return competitor
```

### 4. Mock Stripe Mode

All billing tests run with empty `STRIPE_SECRET_KEY`, so subscription creation happens directly in the database.

**How it works:** The billing service checks if `STRIPE_SECRET_KEY` is set. If not, it bypasses Stripe API calls and creates subscription records with mock Stripe IDs like `mock_sub_XXXXXX`.

### 5. Table Truncation

Every test starts with clean tables via `TRUNCATE CASCADE`. Non-self DB connections are terminated first to prevent deadlocks.

**Fixture implementation:**
```python
@pytest.fixture(autouse=True)
async def setup_db():
    # Create tables before test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Truncate after test
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
```

---

## Writing New Tests

### Basic Test Template

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_feature_name(client: AsyncClient, db: AsyncSession):
    # Arrange: Set up test data
    headers = await register_and_login(client, "test@example.com")

    # Act: Perform the action
    resp = await client.get("/api/v1/endpoint", headers=headers)

    # Assert: Verify the outcome
    assert resp.status_code == 200
    data = resp.json()
    assert data["field"] == "expected_value"
```

### Testing Authenticated Endpoints

Use the `auth_headers` fixture or `register_and_login()` helper:

```python
async def test_with_auth(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/competitors/", headers=auth_headers)
    assert resp.status_code == 200
```

### Testing Unauthenticated Access

Omit the `headers` parameter:

```python
async def test_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/competitors/")
    assert resp.status_code == 401
```

### Testing Pagination

```python
async def test_pagination(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/competitors/?page=2&per_page=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 10
```

### Testing Validation Errors

```python
async def test_validation_error(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/competitors/", json={"name": ""}, headers=auth_headers)
    assert resp.status_code == 422
```

### Testing Database State

Access the `db` fixture directly:

```python
from app.models import Competitor

async def test_db_state(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # Create via API
    resp = await client.post("/api/v1/competitors/", json={...}, headers=auth_headers)
    comp_id = resp.json()["id"]

    # Verify in database
    result = await db.execute(select(Competitor).where(Competitor.id == comp_id))
    competitor = result.scalar_one()
    assert competitor.name == "Expected Name"
```

---

## Test Isolation

Each test runs in complete isolation:

1. **Database:** Tables are truncated between tests (no shared state)
2. **Auth:** Each test creates its own users with unique emails
3. **Async context:** Single event loop for all tests (session-scoped)

**Important:** Do NOT manually delete rows in tests. The `setup_db` fixture handles cleanup automatically.

---

## Debugging Failed Tests

### View Detailed Output

```bash
pytest tests/test_competitors.py::test_name -vv
```

### Stop on First Failure

```bash
pytest -x
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Print Database State

```python
async def test_debug(client: AsyncClient, db: AsyncSession):
    result = await db.execute(select(Competitor))
    competitors = result.scalars().all()
    print(f"Database has {len(competitors)} competitors")
    for c in competitors:
        print(f"  - {c.name}: {c.status}")
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [README](README.md)*
