# QA Engineer Guide

**For QA Engineers:** This guide covers how to test the TrendScout service, including running the backend test suite, understanding test coverage, verifying API endpoints, and validating feature behavior. TrendScout is an AI-powered product research SaaS that discovers trending products using multi-source data aggregation and weighted scoring. All tests run in mock mode -- no real Stripe, AI, or external API calls are made during testing.

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

### Verify Dashboard Build

```bash
cd trendscout/dashboard
npm run build
```

### Verify Landing Page Build

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

### `db` (AsyncSession)
A raw database session for direct model manipulation (e.g., inserting `ResearchResult` records that are normally created by Celery tasks).

### `auth_headers` (dict)
Registers a new user and returns `{"Authorization": "Bearer <token>"}`. Each test gets a fresh user.

### `register_and_login(client, email?)` (helper function)
Registers a user with the given (or random) email and returns auth headers. Use when you need multiple users in a test (e.g., for user isolation checks).

### `setup_db` (autouse fixture)
Creates all tables before each test and truncates all tables after each test with `CASCADE`. Terminates all non-self database connections before truncation to prevent deadlocks.

---

## API Documentation

| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8101/docs |
| ReDoc | http://localhost:8101/redoc |
| OpenAPI JSON | http://localhost:8101/openapi.json |

---

## API Response Format

### Paginated List Response

All list endpoints return:

```json
{
  "items": [ ... ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Auth Patterns

- **JWT Bearer**: `Authorization: Bearer <access_token>` -- used by dashboard users
- **API Key**: `X-API-Key: <raw_key>` -- used by programmatic integrations
- Unauthenticated requests return `401`
- Accessing another user's resources returns `404` (not `403`, to avoid information leakage)

---

## Current API Endpoint Summary

### Auth Endpoints (`/api/v1/auth/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| POST | `/auth/register` | None | Create account, return JWT tokens | 201, 409, 422 |
| POST | `/auth/login` | None | Login with email/password | 200, 401 |
| POST | `/auth/refresh` | None | Refresh tokens | 200, 401 |
| GET | `/auth/me` | JWT | Get user profile | 200, 401 |
| POST | `/auth/forgot-password` | None | Request password reset | 200 |
| POST | `/auth/provision` | JWT/API Key | Provision user from platform | 201 |

### Research Endpoints (`/api/v1/research/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| POST | `/research/runs` | JWT | Create research run | 201, 401, 403, 422 |
| GET | `/research/runs` | JWT | List runs (paginated) | 200, 401 |
| GET | `/research/runs/{run_id}` | JWT | Get run detail with results | 200, 401, 404 |
| DELETE | `/research/runs/{run_id}` | JWT | Delete run + cascade results | 204, 401, 404 |
| GET | `/research/results/{result_id}` | JWT | Get single result detail | 200, 401, 404 |

### Watchlist Endpoints (`/api/v1/watchlist/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| POST | `/watchlist` | JWT | Add result to watchlist | 201, 401, 403, 404, 409 |
| GET | `/watchlist` | JWT | List items (filter by status) | 200, 401 |
| PATCH | `/watchlist/{item_id}` | JWT | Update status/notes | 200, 401, 404 |
| DELETE | `/watchlist/{item_id}` | JWT | Remove from watchlist | 204, 401, 404 |

### Source Endpoints (`/api/v1/sources/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| POST | `/sources` | JWT | Create source config | 201, 400, 401 |
| GET | `/sources` | JWT | List source configs | 200, 401 |
| PATCH | `/sources/{config_id}` | JWT | Update config | 200, 401, 404 |
| DELETE | `/sources/{config_id}` | JWT | Delete config | 204, 401, 404 |

### Billing Endpoints (`/api/v1/billing/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| GET | `/billing/plans` | None | List all plan tiers | 200 |
| POST | `/billing/checkout` | JWT | Create Stripe checkout session | 201, 400, 401 |
| POST | `/billing/portal` | JWT | Create Stripe portal session | 200, 400, 401 |
| GET | `/billing/current` | JWT | Get current subscription | 200, 401 |
| GET | `/billing/overview` | JWT | Full billing + usage overview | 200, 401 |

### API Key Endpoints (`/api/v1/api-keys/`)

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| POST | `/api-keys` | JWT | Create API key (raw key returned once) | 201, 401 |
| GET | `/api-keys` | JWT | List keys (no raw keys) | 200, 401 |
| DELETE | `/api-keys/{key_id}` | JWT | Revoke (deactivate) key | 204, 401, 404 |

### Analytics / Utility Endpoints

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|-------------|
| GET | `/usage` | API Key | Usage metrics for API consumers | 200, 401 |
| GET | `/health` | None | Health check with service metadata | 200 |

---

## Verification Checklist

Before marking a release as ready:

- [ ] All backend tests pass: `pytest` (158 tests)
- [ ] Dashboard builds successfully: `cd dashboard && npm run build`
- [ ] Landing page builds successfully: `cd landing && npm run build`
- [ ] Backend starts without errors: `uvicorn app.main:app --port 8101`
- [ ] Swagger docs load at http://localhost:8101/docs
- [ ] Health endpoint returns `{"status": "ok"}` at `/api/v1/health`

---

## Feature Verification Table

| Feature | What to Test | Expected Behavior |
|---------|-------------|-------------------|
| **Registration** | POST `/auth/register` with valid email/password | 201 + JWT tokens returned |
| **Duplicate Email** | Register same email twice | Second attempt returns 409 |
| **Login** | POST `/auth/login` with correct credentials | 200 + JWT tokens |
| **Invalid Login** | POST `/auth/login` with wrong password | 401 |
| **Token Refresh** | POST `/auth/refresh` with refresh token | 200 + new token pair |
| **Profile** | GET `/auth/me` with Bearer token | 200 + user profile with plan=free |
| **Plan Listing** | GET `/billing/plans` | 200 + 3 plans (free, pro, enterprise) |
| **Checkout** | POST `/billing/checkout` for "pro" plan | 201 + checkout_url and session_id |
| **Free Plan Checkout** | POST `/billing/checkout` for "free" plan | 400 error |
| **Create Research Run** | POST `/research/runs` with keywords and sources | 201 + run with status=pending |
| **Plan Limit Enforcement** | Create 6 runs on free plan (limit=5) | 6th run returns 403 |
| **List Runs** | GET `/research/runs` after creating runs | Paginated list, newest first |
| **Run Detail** | GET `/research/runs/{id}` | 200 + run with results array |
| **Delete Run** | DELETE `/research/runs/{id}` | 204 + run no longer retrievable |
| **Add to Watchlist** | POST `/watchlist` with valid result_id | 201 + item with status=watching |
| **Duplicate Watchlist** | Add same result twice | Second attempt returns 409 |
| **Watchlist Capacity** | Add 26 items on free plan (limit=25) | 26th item returns 403 |
| **Filter Watchlist** | GET `/watchlist?status=imported` | Only imported items returned |
| **Update Watchlist** | PATCH `/watchlist/{id}` with status=imported | 200 + status updated |
| **Create Source** | POST `/sources` with aliexpress type | 201 + config with has_credentials flag |
| **Invalid Source Type** | POST `/sources` with type=amazon | 400 error |
| **Credential Redaction** | Any source response | No raw credentials, only has_credentials boolean |
| **Create API Key** | POST `/api-keys` | 201 + raw key returned (shown once) |
| **API Key Auth** | GET `/usage` with X-API-Key header | 200 + usage data |
| **Revoke API Key** | DELETE `/api-keys/{id}` | 204 + key marked inactive |
| **User Isolation** | Access another user's run/watchlist/source | Always returns 404 |
| **Unauthenticated Access** | Any protected endpoint without token | Always returns 401 |
