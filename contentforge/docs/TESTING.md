# ContentForge Testing Guide

> Part of [ContentForge](README.md) documentation

Testing infrastructure, coverage, fixtures, and patterns for the ContentForge backend.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and framework |
| **pytest-asyncio** | Async test support for FastAPI |
| **httpx (AsyncClient)** | HTTP test client (replaces requests for async) |
| **SQLAlchemy (async)** | Direct DB access in test fixtures |
| **PostgreSQL 16** | Test database (same as dev, tables truncated between tests) |

---

## Running Tests

```bash
# All tests (116 across 7 files)
make test-backend

# With coverage
cd backend && pytest --cov=app --cov-report=html tests/

# Single file
cd backend && pytest tests/test_content.py -v

# Single test
cd backend && pytest tests/test_content.py::test_create_generation_job_from_url -v
```

---

## Test Coverage

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_auth.py` | 10 | Registration, login, refresh, profile, duplicate email (409), invalid credentials (401) |
| `test_content.py` | 13 | Generation lifecycle, plan limits (403), pagination, bulk generation, user isolation, image jobs |
| `test_templates.py` | 17 | Custom template CRUD, system template protection (403), partial updates, user isolation, prompt override |
| `test_images.py` | 12 | Image listing, pagination, retrieval, deletion, user isolation, cross-job images, job independence |
| `test_billing.py` | 9 | Plan listing, checkout, duplicate subscription (400), billing overview, current subscription |
| `test_api_keys.py` | 5 | Key creation (raw key returned), listing (no raw key), revocation, API key auth, invalid key (401) |
| `test_health.py` | 1 | Health endpoint returns status ok |
| **Total** | **116** | |

---

## Test File Structure

```
backend/tests/
├── conftest.py          # Shared fixtures and test infrastructure
├── test_auth.py         # Authentication and user management
├── test_content.py      # Content generation lifecycle
├── test_templates.py    # Template CRUD and system template protection
├── test_images.py       # Image processing and retrieval
├── test_billing.py      # Subscription and billing
├── test_api_keys.py     # API key management and authentication
└── test_health.py       # Health check endpoint
```

---

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop shared by all tests (pytest-asyncio) |
| `setup_db` | function (autouse) | Creates tables once, truncates all tables after each test |
| `db` | function | Raw `AsyncSession` for direct database operations |
| `client` | function | `httpx.AsyncClient` configured for the FastAPI app |
| `auth_headers` | function | Pre-authenticated Bearer token headers |

### Helper Function

```python
async def register_and_login(client, email=None) -> dict
```

Registers a user and returns `{"Authorization": "Bearer <token>"}` headers. If no email is provided, a random one is generated.

---

## Database Isolation

Each test is fully isolated via table truncation:

1. **Tables created** once at session start via `Base.metadata.create_all`
2. **Connections terminated** after each test (prevents deadlocks on FK constraints)
3. **Tables truncated** with `CASCADE` in reverse dependency order

> **Important:** Schema-based isolation is used when running alongside other services. The `contentforge_test` schema is set via SQLAlchemy `connect` event listener.

---

## Mock Mode

ContentForge tests run without external dependencies:

### Stripe Mock

When `STRIPE_SECRET_KEY` is not set, `POST /billing/checkout` creates subscriptions directly in the database. No Stripe API calls are made.

### AI Mock

When `ANTHROPIC_API_KEY` is not set, `generate_mock_content()` produces deterministic text based on product data. No Claude API calls or costs.

---

## Writing Tests

### Naming Convention

Use descriptive names that explain the scenario:

```python
# Good
def test_create_generation_job_from_url()
def test_free_tier_generation_limit_enforced()
def test_user_cannot_access_another_users_job()
def test_system_template_cannot_be_deleted()

# Bad
def test_generation()
def test_limits()
```

### Standard Pattern

```python
@pytest.mark.asyncio
async def test_feature_name(client: AsyncClient):
    # 1. Arrange
    headers = await register_and_login(client)

    # 2. Act
    resp = await client.post(
        "/api/v1/content/generate",
        json={"source_type": "url", "source_url": "https://example.com"},
        headers=headers
    )

    # 3. Assert
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
```

### Common Patterns

**Plan limits:**
```python
for i in range(10):  # Free tier limit
    resp = await client.post("/api/v1/content/generate", json={...}, headers=headers)
    assert resp.status_code == 201

resp = await client.post("/api/v1/content/generate", json={...}, headers=headers)
assert resp.status_code == 403
```

**User isolation:**
```python
user1 = await register_and_login(client, "user1@example.com")
user2 = await register_and_login(client, "user2@example.com")

resp1 = await client.post("/api/v1/content/generate", json={...}, headers=user1)
resource_id = resp1.json()["id"]

resp2 = await client.get(f"/api/v1/content/jobs/{resource_id}", headers=user2)
assert resp2.status_code == 404
```

### Best Practices

1. **One behavior per test** -- keep tests focused on a single scenario
2. **Assert status code first** before calling `.json()` on the response
3. **Use `register_and_login` helper** for all authenticated test setup
4. **Test edge cases** -- empty lists, plan limits, user isolation, null/optional fields
5. **Clean up is automatic** -- `setup_db` handles truncation; only close manually-created DB connections

---

## Debugging

```bash
pytest tests/test_content.py -v        # Verbose output
pytest tests/test_content.py -s        # Show print statements
pytest tests/test_content.py --pdb     # Drop into debugger on failure
```

---

## CI/CD

Tests run on every push and pull request:

```bash
make test-backend
```

PostgreSQL 16 and Redis 7 are provisioned as service containers. All 116 tests must pass before merging.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [README](README.md)*
