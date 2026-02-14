# ShopChat Testing Guide

> Part of [ShopChat](README.md) documentation

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and framework |
| pytest-asyncio | Async test support for FastAPI |
| httpx | Async HTTP test client |
| SQLAlchemy + asyncpg | Test database operations |
| PostgreSQL 16 | Test database (truncated between tests) |

## Running Tests

```bash
# All tests (from shopchat/ directory)
make test-backend

# From backend/ directory
pytest -v

# Specific file
pytest tests/test_chatbots.py -v          # 21 tests
pytest tests/test_knowledge.py -v          # 26 tests
pytest tests/test_conversations.py -v      # 17 tests
pytest tests/test_widget.py -v             # 16 tests

# Single test
pytest tests/test_widget.py::test_widget_chat_with_knowledge_base -v

# Stop on first failure
pytest -v -x

# Filter by keyword
pytest -v -k "chatbot"

# Coverage
pytest --cov=app --cov-report=html
pytest --cov=app --cov-report=term-missing
```

## Coverage Summary

ShopChat has **113 backend tests**.

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_knowledge.py` | 26 | Knowledge base CRUD, plan limits, ownership, source types, pagination, scoping |
| `test_chatbots.py` | 21 | Chatbot CRUD, widget key uniqueness, user scoping, theme config, validation |
| `test_conversations.py` | 17 | List, detail (with messages), end, rate (1-5 range), pagination, scoping |
| `test_widget.py` | 16 | Public config, chat flow, AI responses, knowledge base context, product suggestions |
| `test_auth.py` | 10 | Register, login, refresh, profile, duplicate email, invalid credentials |
| `test_billing.py` | 9 | Plan listing, checkout, duplicate subscription, billing overview, current subscription |
| `test_api_keys.py` | 5 | Create, list, revoke, auth via X-API-Key, invalid key |
| `test_health.py` | 1 | Health check endpoint returns 200 with service metadata |
| **Total** | **113** | |

## Key Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single asyncio event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before each test; truncates all tables with CASCADE after; terminates non-self DB connections |
| `db` | function | Raw async database session for direct model operations |
| `client` | function | `httpx.AsyncClient` bound to the FastAPI app at `http://test` |
| `auth_headers` | function | Registers a fresh user and returns `{"Authorization": "Bearer <token>"}` |

### Helper Functions

| Helper | Location | Purpose |
|--------|----------|---------|
| `register_and_login(client, email)` | `conftest.py` | Registers user, returns auth headers (random email if not provided) |
| `create_test_chatbot(client, headers, name)` | `test_chatbots.py` | Creates chatbot via API, returns JSON response |
| `create_test_entry(client, headers, chatbot_id, ...)` | `test_knowledge.py` | Creates knowledge base entry via API |
| `send_widget_message(client, widget_key, ...)` | `test_conversations.py` | Sends chat message through public widget endpoint |
| `create_chatbot_and_conversation(client, headers, ...)` | `test_conversations.py` | Creates chatbot + starts conversation in one step |
| `create_authenticated_chatbot(client, ...)` | `test_widget.py` | Registers user, creates chatbot, returns both |

## Test Database

Tests use a dedicated PostgreSQL schema (`shopchat_test`) for isolation:
- Same PostgreSQL instance as development
- All queries scoped via `search_path`
- Tables created before each test, truncated after with `CASCADE`
- Non-self connections terminated to prevent deadlocks

## Writing New Tests

### Pattern

All tests use Arrange-Act-Assert with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_create_chatbot(client: AsyncClient, auth_headers: dict):
    """Test creating a new chatbot."""
    # Arrange
    payload = {"name": "Test Bot", "personality": "friendly", "welcome_message": "Hello!"}

    # Act
    response = await client.post("/api/v1/chatbots", json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Bot"
    assert "widget_key" in data
```

### Naming Convention

- `test_<action>_<expected_result>` -- e.g., `test_create_chatbot_returns_201`
- `test_<action>_<error_case>` -- e.g., `test_delete_chatbot_returns_404_when_not_found`

Every test function must have a docstring.

### Key Test Scenarios

**Public widget endpoints (no auth):**
```python
@pytest.mark.asyncio
async def test_widget_chat_no_auth(client: AsyncClient):
    """Widget chat works without authentication."""
    headers = await register_and_login(client)
    bot = await client.post("/api/v1/chatbots", json={"name": "Bot"}, headers=headers)
    widget_key = bot.json()["widget_key"]

    response = await client.post("/api/v1/widget/chat", json={
        "widget_key": widget_key, "visitor_id": "v-123", "message": "Hello"
    })
    assert response.status_code == 200
```

**Cross-user security (returns 404, not 403):**
```python
@pytest.mark.asyncio
async def test_cross_user_access(client: AsyncClient):
    """Users cannot access other users' chatbots."""
    headers_a = await register_and_login(client, "a@test.com")
    bot = await client.post("/api/v1/chatbots", json={"name": "Bot"}, headers=headers_a)

    headers_b = await register_and_login(client, "b@test.com")
    response = await client.get(f"/api/v1/chatbots/{bot.json()['id']}", headers=headers_b)
    assert response.status_code == 404
```

**Plan limits (403 on exceed):**
```python
@pytest.mark.asyncio
async def test_knowledge_base_limit(client: AsyncClient, auth_headers: dict):
    """Free plan limits knowledge base entries."""
    bot = await client.post("/api/v1/chatbots", json={"name": "Bot"}, headers=auth_headers)
    chatbot_id = bot.json()["id"]

    for i in range(10):
        resp = await client.post("/api/v1/knowledge",
            json={"chatbot_id": chatbot_id, "title": f"E{i}", "content": "T"}, headers=auth_headers)
        assert resp.status_code == 201

    resp = await client.post("/api/v1/knowledge",
        json={"chatbot_id": chatbot_id, "title": "E11", "content": "T"}, headers=auth_headers)
    assert resp.status_code == 403
```

## Debugging

```bash
# Full output
pytest -v -s tests/test_chatbots.py

# Last failed only
pytest --lf

# Drop into PDB on failure
pytest tests/test_chatbots.py::test_create_chatbot -v -s --pdb
```

## Continuous Integration

Tests run automatically on every commit via GitHub Actions:
1. Starts PostgreSQL and Redis containers
2. Sets up the test schema
3. Runs all 113 backend tests
4. Generates coverage reports
5. Fails the build if any test fails or coverage drops below threshold

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [README](README.md)*
