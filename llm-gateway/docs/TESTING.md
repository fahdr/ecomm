# LLM Gateway Testing

> Part of [LLM Gateway](README.md) documentation

Test infrastructure, running tests, and coverage.

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and fixtures |
| **pytest-asyncio** | Async test support |
| **httpx** | AsyncClient for API testing |
| **asyncpg** | Raw connection for schema management |
| **SQLAlchemy** | ORM for test fixtures |

## Test Metrics

| Metric | Value |
|--------|-------|
| **Total Tests** | 42 |
| **Test Files** | 8 |
| **Coverage** | ~90% |

## Running Tests

### All Tests

```bash
cd /workspaces/ecomm/llm-gateway/backend
pytest
```

### Verbose Output

```bash
pytest -v
```

### Specific Test File

```bash
pytest tests/test_generate.py -v
```

### With Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Show Print Statements

```bash
pytest -v -s
```

### Stop on First Failure

```bash
pytest -x
```

## Test Coverage by File

| Test File | Focus | Tests |
|-----------|-------|-------|
| `test_generate.py` | Main generation endpoint | 8 |
| `test_providers.py` | Provider CRUD endpoints | 7 |
| `test_overrides.py` | Override CRUD endpoints | 5 |
| `test_usage.py` | Usage analytics endpoints | 6 |
| `test_cost_service.py` | Cost calculation logic | 4 |
| `test_providers_unit.py` | Provider implementations | 6 |
| `test_health.py` | Health check endpoints | 2 |
| **Total** | | **42** |

## Test Fixtures

### conftest.py

Provides session-scoped and per-test fixtures.

#### Session-Scoped Fixtures

##### `event_loop`

Single event loop for all async tests.

##### `create_tables`

- Terminates stale DB connections
- Drops and recreates `llm_gateway_test` schema
- Creates all tables once per session
- Overrides `get_db` dependency in FastAPI app

#### Per-Test Fixtures

##### `truncate_tables`

Auto-runs before every test:
- Truncates all tables (fast isolation)
- Resets Redis cache and rate limiter
- Disposes stale DB connections

##### `db`

Provides an async database session for tests:
```python
async def test_create_provider(db: AsyncSession):
    config = ProviderConfig(name="claude", ...)
    db.add(config)
    await db.flush()
```

##### `client`

Provides an httpx AsyncClient for API tests:
```python
async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
```

##### `auth_headers`

Authenticated headers with service key:
```python
async def test_generate(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp.status_code == 200
```

## Schema Isolation Pattern

The gateway uses a dedicated `llm_gateway_test` schema to avoid conflicts with other services sharing the PostgreSQL database.

### Why Schema Isolation?

- **Shared Database**: All services use the same PostgreSQL instance
- **Test Conflicts**: Without isolation, `pg_terminate_backend` would kill other services' connections
- **Clean State**: Each test starts with truncated tables

### How It Works

1. **Session Setup**: `create_tables` fixture:
   - Terminates stale connections (filtered by schema)
   - Drops and recreates `llm_gateway_test` schema
   - Creates tables in the test schema

2. **Per-Test Setup**: `truncate_tables` fixture:
   - Truncates all tables (no DROP/CREATE overhead)
   - Resets Redis cache

3. **Connection Handling**: All DB connections set `search_path`:
   ```python
   @event.listens_for(engine.sync_engine, "connect")
   def set_search_path(dbapi_conn, connection_record):
       cursor = dbapi_conn.cursor()
       cursor.execute("SET search_path TO llm_gateway_test")
       cursor.close()
   ```

## Example Tests

### Testing Generation Endpoint

```python
async def test_generate_success(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # Create a provider
    config = ProviderConfig(
        name="claude",
        display_name="Anthropic Claude",
        api_key_encrypted="test-key",
        models=["claude-sonnet-4-5-20250929"],
        is_enabled=True,
    )
    db.add(config)
    await db.flush()

    # Mock provider call (or use a test provider)
    body = {
        "user_id": "test_user",
        "service": "trendscout",
        "prompt": "Hello world",
    }
    resp = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert data["cached"] is False
```

### Testing Cache Hit

```python
async def test_cache_hit(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # Setup provider...
    body = {"user_id": "test", "service": "test", "prompt": "Same prompt"}

    # First request (cache miss)
    resp1 = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp1.json()["cached"] is False

    # Second request (cache hit)
    resp2 = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp2.json()["cached"] is True
```

### Testing Rate Limiting

```python
async def test_rate_limit(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # Create provider with low RPM
    config = ProviderConfig(name="claude", rate_limit_rpm=2, ...)
    db.add(config)
    await db.flush()

    body = {"user_id": "test", "service": "test", "prompt": "Test"}

    # First 2 requests succeed
    await client.post("/api/v1/generate", json=body, headers=auth_headers)
    await client.post("/api/v1/generate", json=body, headers=auth_headers)

    # Third request is rate-limited
    resp = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp.status_code == 429
```

### Testing Provider Override

```python
async def test_customer_override(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # Create two providers
    claude = ProviderConfig(name="claude", priority=10, ...)
    openai = ProviderConfig(name="openai", priority=20, ...)
    db.add_all([claude, openai])

    # Create override for specific user
    override = CustomerOverride(
        user_id="premium_user",
        service_name=None,
        provider_name="openai",
        model_name="gpt-4o",
    )
    db.add(override)
    await db.flush()

    # Request should use OpenAI for premium_user
    body = {"user_id": "premium_user", "service": "test", "prompt": "Test"}
    resp = await client.post("/api/v1/generate", json=body, headers=auth_headers)
    assert resp.json()["provider"] == "openai"
```

## Troubleshooting Tests

### Test Hangs on Schema Creation

**Symptom**: `create_tables` fixture times out.

**Solution**: Manually kill stale connections:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'dropshipping'
  AND query LIKE '%llm_gateway_test%';
```

### Redis Connection Errors

**Symptom**: `redis.exceptions.ConnectionError`

**Solution**: Ensure Redis is running:
```bash
docker ps | grep redis
```

### Provider API Calls in Tests

**Symptom**: Tests make real API calls (slow, costs money).

**Solution**: Mock provider responses or use `custom` provider with mock endpoint.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
