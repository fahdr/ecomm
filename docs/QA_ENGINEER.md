# QA Engineer Guide

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** 8.3+ | Test runner and assertion framework |
| **pytest-asyncio** 0.24+ | Async test support (all backend code is async) |
| **httpx** 0.28+ | HTTP client used to call API endpoints in tests |
| **Ruff** 0.8+ | Linter — catches code quality issues |
| **ESLint** | Linter for TypeScript/Next.js code |

## Running Tests

```bash
cd /workspaces/ecomm/backend

# Run all tests
pytest

# Verbose output (see each test name and result)
pytest -v

# Run a specific test file
pytest tests/test_health.py

# Run tests matching a keyword
pytest -k "health"

# Stop on first failure
pytest -x
```

### VS Code Integration

The devcontainer configures pytest in VS Code automatically:
- Tests appear in the **Test Explorer** sidebar
- Click the play button next to any test to run or debug it
- Breakpoints work in test files

## Current Test Coverage

| Test File | Tests | What it covers |
|-----------|-------|----------------|
| `tests/test_health.py` | 1 | `GET /api/v1/health` returns 200 with `{"status": "ok"}` |

## Test Structure

### Directory Layout

```
backend/tests/
├── __init__.py
├── conftest.py          # Shared fixtures (client)
└── test_health.py       # Health endpoint tests
```

### Fixtures (`conftest.py`)

The `client` fixture provides an async HTTP client wired directly to the FastAPI app (no network required):

```python
@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
```

Use this fixture in any test by adding `client` as a parameter.

### Writing a Test

All tests are async. Use the `client` fixture to call endpoints:

```python
import pytest

@pytest.mark.asyncio
async def test_example(client):
    response = await client.get("/api/v1/some-endpoint")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
```

For POST/PATCH requests:

```python
async def test_create_something(client):
    response = await client.post("/api/v1/resource", json={
        "name": "Test",
        "value": 42,
    })
    assert response.status_code == 201
```

### Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"      # No need for @pytest.mark.asyncio on every test
testpaths = ["tests"]       # pytest looks here by default
```

## API Documentation

The backend auto-generates interactive API docs:

| URL | Format |
|-----|--------|
| `http://localhost:8000/docs` | Swagger UI — interactive, try-it-out interface |
| `http://localhost:8000/redoc` | ReDoc — clean read-only documentation |
| `http://localhost:8000/openapi.json` | Raw OpenAPI 3.x schema |

Use Swagger UI to manually test endpoints during exploratory testing.

## API Response Format

All endpoints follow a consistent format. Use these patterns for assertions:

### Success Response

```json
{
  "data": { ... },
  "error": null
}
```

### Error Response

```json
{
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

### Paginated Response

Query: `?page=1&per_page=20`

```json
{
  "data": [ ... ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

## Current API Endpoints

| Method | Path | Auth | Status |
|--------|------|------|--------|
| `GET` | `/` | No | Implemented — returns API info |
| `GET` | `/api/v1/health` | No | Implemented — DB connectivity check |

## Planned Test Areas by Feature

| Feature | What to test |
|---------|-------------|
| **2. Auth** | Registration, login, token refresh, password reset, protected routes, invalid credentials, expired tokens |
| **3. Stores** | CRUD operations, slug generation, tenant isolation (user A can't see user B's stores), soft-delete |
| **4. Storefront** | Public store resolution by slug, 404 for unknown slugs, SSR data fetching |
| **5. Products** | CRUD, image upload, pagination, search, filtering, public product listing |
| **6. Checkout** | Cart validation, Stripe session creation, webhook handling, order creation |
| **7. Subscriptions** | Plan creation, upgrade/downgrade, cancellation, plan limit enforcement |
| **8. Research** | Celery task execution, scoring algorithm, data source integration |
| **9. Import** | AI content generation, image processing, pricing calculation |

## Environment

Tests run against the same PostgreSQL and Redis instances used for development. The `conftest.py` `client` fixture connects to the FastAPI app in-process (no server needed).

Environment variables are inherited from the devcontainer's `docker-compose.yml` — no additional test configuration is required.

## Linting

```bash
# Python — check for issues
cd /workspaces/ecomm/backend
ruff check .

# Python — auto-fix
ruff check --fix .

# TypeScript — dashboard
cd /workspaces/ecomm/dashboard
npm run lint

# TypeScript — storefront
cd /workspaces/ecomm/storefront
npm run lint
```
