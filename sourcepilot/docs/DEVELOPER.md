# SourcePilot -- Developer Documentation

## Overview

SourcePilot is an automated supplier product import service for dropshipping. It enables merchants to search supplier catalogs (AliExpress, CJ Dropshipping, Spocket), preview products, import them into connected stores, and monitor supplier price changes over time.

- **Service name**: `sourcepilot`
- **Backend port**: 8109
- **Dashboard port**: 3109
- **Stack**: FastAPI (Python) backend, Next.js (TypeScript) dashboard
- **Database**: PostgreSQL with `sourcepilot` schema (test: `sourcepilot_test`)
- **Task queue**: Celery with Redis broker
- **Auth**: JWT Bearer tokens + API key (`X-API-Key` header)

---

## Architecture

```
sourcepilot/
  backend/
    app/
      api/           # FastAPI route handlers
      config.py      # Pydantic Settings (env vars)
      constants/     # Plan tier definitions (plans.py)
      database.py    # Async SQLAlchemy engine + session factory
      main.py        # FastAPI app entry point, lifespan, router registration
      models/        # SQLAlchemy ORM models
      schemas/       # Pydantic request/response schemas
      services/      # Business logic layer
      tasks/         # Celery app + background tasks
      utils/         # Shared helpers (billing period calculation)
    tests/           # pytest test suite (130 tests, 11 files)
  dashboard/
    src/app/         # Next.js pages (App Router)
    src/components/  # Shared UI components
    src/lib/         # API client, auth helpers
  docs/              # This documentation
```

### Layered Design

1. **API layer** (`app/api/`) -- Route definitions, request validation, HTTP status codes. Depends on services and deps (auth).
2. **Service layer** (`app/services/`) -- Business logic, database queries, plan enforcement. All functions accept an `AsyncSession` and operate within the caller's transaction.
3. **Model layer** (`app/models/`) -- SQLAlchemy ORM models defining the database schema.
4. **Schema layer** (`app/schemas/`) -- Pydantic v2 models for request/response validation and serialization.
5. **Task layer** (`app/tasks/`) -- Celery tasks for background processing (import execution, price sync).

### Database Schema Isolation

All queries are scoped to the `sourcepilot` schema via the PostgreSQL `search_path` connection argument set in `database.py`:

```python
engine = create_async_engine(
    settings.database_url,
    connect_args={"server_settings": {"search_path": "sourcepilot,public"}},
)
```

Tests use a separate `sourcepilot_test` schema. The test engine sets `search_path` via a SQLAlchemy `connect` event listener in `tests/conftest.py`.

### Shared Packages

- **`ecomm_core`**: Auth utilities, billing helpers, database factories, health checks, testing helpers (`register_and_login`).
- **`ecomm_connectors`**: Shopify and WooCommerce platform adapters (used by store connections in production).

---

## Configuration

All settings are loaded from environment variables via `app/config.py` (Pydantic `BaseSettings`):

| Variable | Default | Description |
|---|---|---|
| `SERVICE_NAME` | `sourcepilot` | Internal service identifier |
| `SERVICE_PORT` | `8109` | Backend listen port |
| `DATABASE_URL` | `postgresql+asyncpg://sourcepilot:sourcepilot_dev@localhost:5432/sourcepilot` | Async DB connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `JWT_SECRET_KEY` | `dev-secret-change-in-production` | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `CORS_ORIGINS` | `http://localhost:3109` | Allowed CORS origins (comma-separated) |
| `STRIPE_SECRET_KEY` | `""` (empty = mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | `""` | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | `""` | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | `""` | Stripe Price ID for Enterprise tier |
| `LLM_GATEWAY_URL` | `http://localhost:8200` | LLM Gateway service URL |
| `LLM_GATEWAY_KEY` | `dev-gateway-key` | LLM Gateway API key |
| `ANTHROPIC_API_KEY` | `""` | Anthropic API key (for direct Claude calls) |

---

## Database Models

### User (`users` table)

Core user account. Fields: `id` (UUID), `email` (unique), `hashed_password`, `is_active`, `plan` (PlanTier enum: free/pro/enterprise), `stripe_customer_id`, `external_platform_id`, `external_store_id`, `created_at`, `updated_at`.

The `plan` field is denormalized from the Subscription model for fast lookups. It is updated whenever the subscription changes (via webhook or checkout).

### Subscription (`subscriptions` table)

Stripe subscription record. Fields: `id`, `user_id` (FK -> users), `stripe_subscription_id` (unique), `stripe_price_id`, `plan` (PlanTier), `status` (SubscriptionStatus: active/trialing/past_due/canceled/unpaid/incomplete), `current_period_start`, `current_period_end`, `cancel_at_period_end`, `trial_start`, `trial_end`, `created_at`, `updated_at`.

### ImportJob (`import_jobs` table)

A single product import operation. Fields: `id`, `user_id` (FK -> users), `store_id` (nullable UUID), `source` (ImportSource: aliexpress/cjdropship/spocket/manual), `source_url`, `source_product_id`, `status` (ImportJobStatus: pending/running/completed/failed/cancelled), `product_data` (JSON), `config` (JSON), `error_message`, `created_product_id`, `progress_percent` (0-100), `created_at`, `updated_at`.

Job lifecycle: `pending` -> `running` -> `completed` | `failed` | `cancelled`.

### ImportHistory (`import_history` table)

Audit log for import job lifecycle events. Fields: `id`, `user_id` (FK -> users), `import_job_id` (FK -> import_jobs, CASCADE), `action` (string: created/failed/retried/cancelled), `details` (JSON), `created_at`.

### SupplierAccount (`supplier_accounts` table)

Supplier platform credentials. Fields: `id`, `user_id` (FK -> users), `name`, `platform` (string: aliexpress/cjdropshipping/spocket), `credentials` (JSON), `is_active`, `last_synced_at`, `created_at`, `updated_at`.

Duplicate detection: unique constraint on `(user_id, name, platform)` enforced at the service layer.

### StoreConnection (`store_connections` table)

Link to a dropshipping store. Fields: `id`, `user_id` (FK -> users), `store_name`, `platform` (shopify/woocommerce), `store_url`, `api_key`, `is_default` (boolean), `created_at`, `updated_at`.

Business rules:
- First connection per user is auto-set as default.
- Only one connection per user can have `is_default=True`.
- Deleting the default promotes the next oldest connection.
- Duplicate `store_url` per user is rejected.

### PriceWatch (`price_watches` table)

Supplier product price monitor. Fields: `id`, `user_id` (FK -> users), `store_id` (nullable UUID, aliased as `connection_id` in API), `source`, `source_product_id`, `product_url`, `source_url`, `threshold_percent` (Decimal, default 10.0), `last_price`, `current_price`, `price_changed` (boolean), `last_checked_at`, `is_active`, `created_at`, `updated_at`.

The `connection_id` in the API maps to the `store_id` column in the database.

### ProductCache (`product_cache` table)

Time-limited cache of supplier product data (24-hour TTL). Fields: `id`, `source` (ImportSource), `source_product_id`, `source_url`, `product_data` (JSON), `expires_at`, `created_at`.

Logical unique key: `(source, source_product_id)`. Expired entries are filtered out with `expires_at > now()`.

### ApiKey (`api_keys` table)

Programmatic access tokens. Fields: `id`, `user_id` (FK -> users), `name`, `key_hash` (SHA-256, unique), `key_prefix` (first 12 chars), `scopes` (ARRAY of strings, default `["read"]`), `is_active`, `last_used_at`, `expires_at`, `created_at`.

Raw key format: `so_live_{32-char-urlsafe-token}`. Only returned once at creation.

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Authentication (`/auth`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/auth/register` | None | 201 | Register new account. Returns JWT pair. |
| POST | `/auth/login` | None | 200 | Login with email/password. Returns JWT pair. |
| POST | `/auth/refresh` | None | 200 | Exchange refresh token for new JWT pair. |
| GET | `/auth/me` | JWT | 200 | Get authenticated user profile. |
| POST | `/auth/forgot-password` | None | 200 | Request password reset (stub). |
| POST | `/auth/provision` | JWT or API Key | 201 | Provision user from dropshipping platform. |

### Imports (`/imports`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/imports` | JWT | 201 | Create single import job. Dispatches Celery task. Checks plan limits. |
| GET | `/imports` | JWT | 200 | List imports with pagination (`skip`, `limit`) and optional filters (`status`, `store_id`). |
| GET | `/imports/{job_id}` | JWT | 200 | Get import job details. |
| POST | `/imports/bulk` | JWT | 201 | Create multiple import jobs (max 50 URLs). |
| POST | `/imports/{job_id}/cancel` | JWT | 200 | Cancel pending/running import. |
| POST | `/imports/{job_id}/retry` | JWT | 200 | Retry failed/cancelled import. Resets to pending. |

**Plan limit enforcement**: `check_import_limit()` counts imports in the current billing month and compares against `PLAN_LIMITS[user.plan].max_items`.

**Import job creation body** (`ImportJobCreate`):
```json
{
  "product_url": "https://aliexpress.com/item/...",
  "source": "aliexpress",
  "store_id": "uuid-optional",
  "config": {"markup_percent": 30, "tags": ["trending"]}
}
```

**Bulk import body** (`BulkImportCreate`):
```json
{
  "product_urls": ["https://...", "https://..."],
  "source": "aliexpress",
  "store_id": "uuid-optional",
  "config": {}
}
```

### Products (`/products`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| GET | `/products/search` | JWT | 200 | Search supplier catalogs. Query params: `q` (required), `source`, `page`, `page_size`. |
| POST | `/products/preview` | JWT | 200 | Preview a product from a supplier URL. Auto-detects source from URL domain. |

Product preview request:
```json
{
  "url": "https://aliexpress.com/item/123456.html"
}
```

Preview response includes: `title`, `price`, `currency`, `images`, `variants`, `source`, `source_url`, `source_product_id`, `supplier_name`, `rating`, `order_count`, `shipping_info`.

Previewed products are cached in the `product_cache` table (24-hour TTL).

**Note**: Product search and preview currently return mock data. In production, these would call real supplier APIs.

### Suppliers (`/suppliers`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/suppliers/accounts` | JWT | 201 | Connect a new supplier account. |
| GET | `/suppliers/accounts` | JWT | 200 | List all supplier accounts. |
| PUT | `/suppliers/accounts/{id}` | JWT | 200 | Update supplier account. |
| DELETE | `/suppliers/accounts/{id}` | JWT | 204 | Disconnect (delete) supplier account. |

### Connections (`/connections`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/connections` | JWT | 201 | Connect a new store. First connection auto-defaults. |
| GET | `/connections` | JWT | 200 | List all store connections (default first). |
| PUT | `/connections/{id}` | JWT | 200 | Update store connection. |
| DELETE | `/connections/{id}` | JWT | 204 | Disconnect store. Default promotes next. |
| POST | `/connections/{id}/default` | JWT | 200 | Set a connection as the default import target. |

### Price Watches (`/price-watches`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/price-watches` | JWT | 201 | Add price watch. Body: `product_url`, `source`, `threshold_percent`, `connection_id`. |
| GET | `/price-watches` | JWT | 200 | List price watches. Optional filter: `connection_id`. |
| DELETE | `/price-watches/{id}` | JWT | 204 | Remove price watch. |
| POST | `/price-watches/sync` | JWT | 200 | Trigger immediate price sync for all active watches. |

Sync response:
```json
{"total_checked": 5, "total_changed": 2, "total_errors": 0}
```

### Billing (`/billing`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| GET | `/billing/plans` | None | 200 | List all available plans (public). |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe Checkout session. Body: `{"plan": "pro"}`. |
| POST | `/billing/portal` | JWT | 200 | Create Stripe Customer Portal session. |
| GET | `/billing/current` | JWT | 200 | Get current subscription details. |
| GET | `/billing/overview` | JWT | 200 | Get billing overview (plan + subscription + usage). |

### Webhooks (`/webhooks`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/webhooks/stripe` | Stripe signature | 200 | Handle Stripe subscription events. |
| POST | `/webhooks/product-scored` | JWT | 200 | TrendScout integration: auto-import products scoring >= 50. |

### API Keys (`/api-keys`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| POST | `/api-keys` | JWT | 201 | Create API key. Raw key returned ONCE. |
| GET | `/api-keys` | JWT | 200 | List API keys (no raw keys). |
| DELETE | `/api-keys/{id}` | JWT | 204 | Revoke (deactivate) API key. |

### Usage (`/usage`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| GET | `/usage` | JWT or API Key | 200 | Get usage metrics for current billing period. |

### Health (`/health`)

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| GET | `/health` | None | 200 | Service health check. Returns `{"service": "sourcepilot", "status": "ok", "timestamp": "..."}`. |

---

## Plan Tiers and Limits

Defined in `app/constants/plans.py`:

| Tier | Monthly Price | Max Imports (max_items) | Max Secondary | Trial Days | API Access |
|---|---|---|---|---|---|
| Free | $0 | 10 | 25 | 0 | No |
| Pro | $29/mo | 100 | 500 | 14 | Yes |
| Enterprise | $99/mo | Unlimited (-1) | Unlimited (-1) | 14 | Yes |

**Primary resource** (`max_items`): Import jobs per billing month.
**Secondary resource** (`max_secondary`): Price watches.

Stripe Price IDs are injected at startup via `init_price_ids()` in `main.py`.

---

## Authentication

### JWT Flow

1. User registers or logs in, receives `access_token` (15 min) + `refresh_token` (7 days).
2. Access token is sent as `Authorization: Bearer <token>`.
3. When access token expires, exchange refresh token at `POST /auth/refresh`.
4. JWT payload: `{"sub": "<user_uuid>", "type": "access"|"refresh", "exp": <timestamp>}`.

### API Key Flow

1. Create key at `POST /api-keys`. Raw key returned once (format: `so_live_{token}`).
2. Send as `X-API-Key: <raw_key>` header.
3. Key is SHA-256 hashed and compared against stored `key_hash`.
4. Endpoints accepting API keys use `get_current_user_or_api_key` dependency.

### Cross-Service Provisioning

The `POST /auth/provision` endpoint creates users from the dropshipping platform:
- Accepts `email`, `password`, `plan`, `external_platform_id`, `external_store_id`.
- Returns `user_id` and a new `api_key` for the platform to use.
- Requires JWT or API Key auth from an authorized service account.

---

## Background Tasks (Celery)

Celery app is configured in `app/tasks/celery_app.py`:
- Broker: Redis (configurable via `CELERY_BROKER_URL`)
- Result backend: Redis (configurable via `CELERY_RESULT_BACKEND`)
- Default queue: `sourcepilot`
- Serialization: JSON
- Timezone: UTC

### Import Processing

When an import job is created, `process_import_job.delay(str(job.id))` dispatches a Celery task that:
1. Fetches product data from the supplier platform.
2. Updates job status (`running` -> `completed` or `failed`).
3. Updates `progress_percent` for real-time dashboard tracking.
4. Creates a product in the target store on success.

### Price Sync

The `sync_all_prices` function checks all active price watches:
1. Fetches current prices from supplier APIs (mock in development).
2. Compares against `last_price` and sets `price_changed` flag.
3. Updates `current_price` and `last_checked_at` timestamps.

Can be triggered manually via `POST /price-watches/sync` or scheduled via Celery beat.

---

## Running Locally

```bash
# Backend
cd sourcepilot/backend
uvicorn app.main:app --reload --port 8109

# Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --queues=sourcepilot

# Dashboard
cd sourcepilot/dashboard
npm run dev  # runs on port 3109
```

API docs: `http://localhost:8109/docs` (Swagger UI), `http://localhost:8109/redoc`.

---

## Testing

### Test Setup

Tests use a dedicated `sourcepilot_test` PostgreSQL schema for isolation:
1. Schema is dropped and recreated once per session.
2. Tables are truncated between each test.
3. Raw asyncpg manages schema creation (more robust than SQLAlchemy for DDL).
4. NullPool engine prevents connection pooling interference.
5. The FastAPI `get_db` dependency is overridden to use the test session factory.

### Running Tests

```bash
cd sourcepilot/backend
pytest                     # run all tests
pytest -v                  # verbose output
pytest tests/test_imports.py  # specific file
pytest -x                  # stop on first failure
```

### Test Files (130 tests across 11 files)

| File | Coverage |
|---|---|
| `test_auth.py` | Registration, login, refresh, profile, provisioning |
| `test_imports.py` | Create, list, get, cancel, retry, bulk import, plan limits |
| `test_products.py` | Search, preview, URL validation, source detection |
| `test_suppliers.py` | CRUD operations, duplicate detection |
| `test_connections.py` | CRUD operations, default management, duplicate URL |
| `test_price_watch.py` | CRUD operations, sync, filtering by connection_id |
| `test_billing.py` | Plans listing, checkout (mock), portal, overview |
| `test_webhooks_sp.py` | Stripe webhook handling, product-scored webhook |
| `test_api_keys.py` | Create, list, revoke, key auth |
| `test_health.py` | Health check endpoint |

### Test Helpers

- `register_and_login(client)` from `ecomm_core.testing`: Creates a test user and returns auth headers.
- `auth_headers` fixture: Provides pre-authenticated headers for test requests.
- `db` fixture: Provides an async database session within the test schema.
- `client` fixture: Provides an httpx `AsyncClient` wired to the FastAPI app.

---

## Key Implementation Details

### Mock Mode

When `STRIPE_SECRET_KEY` is empty (default in development), all Stripe operations run in mock mode:
- Checkout creates subscriptions directly in the database.
- Portal returns the success URL without hitting Stripe.
- Webhooks accept raw JSON without signature verification.

Product search and preview also use mock data generators with deterministic seeding for reproducible results.

### TrendScout Integration

The `POST /webhooks/product-scored` endpoint receives product scoring events from TrendScout:
- Products scoring >= 50.0 automatically trigger an import job.
- Products below threshold are acknowledged but not imported.
- The auto-import threshold is configurable via `AUTO_IMPORT_SCORE_THRESHOLD`.

### Error Handling Patterns

- **400 Bad Request**: Invalid source type, invalid URL format, non-retryable status.
- **401 Unauthorized**: Missing/invalid/expired token, user not found.
- **403 Forbidden**: Plan import limit exceeded.
- **404 Not Found**: Resource not found or not owned by the requesting user.
- **409 Conflict**: Duplicate email on register, duplicate store URL on connect.

### Important Gotchas

- **UUID serialization**: Always pass UUIDs as strings to Celery `.delay()`.
- **`search_path`**: Any code creating its own DB engine MUST set the schema search path.
- **`pg_terminate_backend`**: Filter by schema in the query to avoid killing other services' connections.
- **Auth register returns 201**: Test helpers should use `assert resp.status_code in (200, 201)`.
- **API 204 No Content**: The frontend API client must check `response.status === 204` before calling `.json()`.
