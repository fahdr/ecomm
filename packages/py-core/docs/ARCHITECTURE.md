# Architecture

> Part of [ecomm_core](README.md) documentation

Module structure, design decisions, and extension points of the `ecomm_core` shared library.

## Design Principles

1. **No Global State:** Factory functions accept settings/dependencies as parameters
2. **Lazy Imports:** Service-specific settings imported inside functions to avoid circular deps
3. **Schema Isolation:** Dedicated PostgreSQL schemas prevent test cross-contamination
4. **Mock Mode:** Stripe integration uses mock mode (empty API key) for local dev and testing
5. **Pluggable Routers:** Services mount only the routers they need

## Module Structure

```
ecomm_core/
├── __init__.py              # Package metadata
├── config.py                # BaseServiceConfig class
├── auth/
│   ├── service.py           # JWT, password, user management
│   ├── deps.py              # FastAPI auth dependencies
│   └── router.py            # Auth endpoints
├── billing/
│   ├── service.py           # Stripe subscription logic
│   ├── router.py            # Billing endpoints
│   └── webhooks.py          # Stripe webhook handler
├── db/
│   └── __init__.py          # Engine and session factory
├── models/
│   ├── base.py              # SQLAlchemy Base
│   ├── user.py              # User + PlanTier enum
│   ├── subscription.py      # Subscription + SubscriptionStatus enum
│   └── api_key.py           # ApiKey
├── schemas/
│   ├── auth.py              # Auth request/response models
│   └── billing.py           # Billing request/response models
├── health.py                # Health check router factory
├── plans.py                 # PlanLimits dataclass and helpers
├── api_keys_router.py       # API key management
├── usage_router.py          # Usage reporting endpoint
├── llm_client.py            # LLM Gateway client
├── middleware.py            # CORS setup
└── testing.py               # Shared test fixtures
```

## Core Components

### 1. Authentication (`auth/`)

Manages JWT tokens, passwords, and API keys. Key functions: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`, `register_user`, `authenticate_user`, `provision_user`, `get_user_by_api_key`.

**Factory Pattern:** `create_get_current_user(get_db)` returns a FastAPI dependency that lazily imports `settings` to avoid circular deps. `create_auth_router(...)` returns a configured APIRouter.

### 2. Billing (`billing/`)

Manages Stripe subscriptions and webhooks. When `stripe_secret_key` is empty, operates in mock mode -- subscriptions created directly, webhook signatures skipped, IDs prefixed with `mock_`.

Key functions: `get_or_create_stripe_customer`, `create_subscription_checkout`, `create_portal_session`, `sync_subscription_from_event`, `get_billing_overview`.

The webhook router accepts `session_factory` (not `get_db`) because webhooks run outside request context. Processes `customer.subscription.created/updated/deleted` events.

### 3. Database (`db/`)

Provides `create_db_engine`, `create_session_factory`, and `create_get_db` for async engine/session management.

**Schema Isolation:** Each service uses `{service_name}_test` PostgreSQL schema, set via SQLAlchemy `connect` event listener on `search_path`.

### 4. Models (`models/`)

All models inherit from `Base` (SQLAlchemy DeclarativeBase).

- **User:** UUID PK, unique email, bcrypt password, plan tier, Stripe customer ID, external platform/store IDs. Relationships: `subscription` (one), `api_keys` (many).
- **Subscription:** Tracks Stripe state -- subscription ID, price ID, plan, status, period dates. When canceled, User.plan reverts to `free`.
- **ApiKey:** SHA-256 hashed key, scopes array, `key_prefix` (first 12 chars), `last_used_at` tracking.
- **PlanTier Enum:** `free`, `pro`, `enterprise`

### 5. Schemas (`schemas/`)

Pydantic v2 request/response models.

- **Auth:** `RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshRequest`, `UserResponse`, `ProvisionRequest`, `ProvisionResponse`
- **Billing:** `PlanInfo`, `CreateCheckoutRequest`, `CheckoutSessionResponse`, `PortalSessionResponse`, `SubscriptionResponse`, `UsageMetric`, `UsageResponse`, `BillingOverviewResponse`

### 6. Plans (`plans.py`)

`PlanLimits` dataclass: `max_items` (-1 = unlimited), `max_secondary`, `price_monthly_cents`, `stripe_price_id`, `trial_days`, `api_access`.

Helpers: `create_default_plan_limits()`, `init_price_ids()`, `resolve_plan_from_price_id()`.

### 7-9. Routers

- **Health** (`health.py`): `create_health_router(service_name)` -- `GET /health` returning service name, status, timestamp.
- **API Keys** (`api_keys_router.py`): CRUD -- `POST` (returns raw key once), `GET` (list), `DELETE` (revoke).
- **Usage** (`usage_router.py`): `create_usage_router(get_db, get_current_user_or_api_key, get_usage_fn)` -- services provide their own `get_usage_fn`.

### 10. LLM Client (`llm_client.py`)

`call_llm()` POSTs to the centralized LLM Gateway. `call_llm_mock()` provides deterministic responses for tests. Benefits: single API key management point, per-customer routing, caching, provider failover.

### 11. Middleware & Config

- `setup_cors(app, cors_origins)` configures CORS middleware.
- `BaseServiceConfig(BaseSettings)` provides defaults for service identity, DB, Redis, JWT, Stripe, LLM Gateway, and CORS. Services subclass to add custom fields.

### 12. Testing (`testing.py`)

`create_test_engine()` (NullPool), `create_test_session_factory()`, and `register_and_login(client)` for auth headers in integration tests.

## Extension Points

**Custom Usage Metrics:** Override `get_usage()` in your service to count specific resources (e.g., research runs, content generations).

**Custom Plan Limits:** Call `create_default_plan_limits()` with service-specific values.

**Additional Auth Endpoints:** Extend the auth router returned by `create_auth_router()`.

**Service-Specific Models:** Add models inheriting from `Base` with ForeignKey to `users.id`.

## Data Flows

- **Registration:** POST `/auth/register` -> `register_user()` -> JWT tokens -> client stores tokens
- **Subscription:** POST `/billing/checkout` -> Stripe checkout (or mock) -> webhook -> `sync_subscription_from_event()` -> plan upgrade
- **API Key Auth:** POST `/api-keys` (JWT) -> key returned once -> client sends `X-API-Key` header -> `get_user_by_api_key()` -> User

## Lessons Learned

- **Schema Isolation:** `pg_terminate_backend` caused cross-contamination; dedicated schemas per service + `search_path` solved it.
- **Lazy Settings Import:** Module-level imports of `settings` in `ecomm_core` caused circular deps; import inside functions instead.
- **Mock Mode for Stripe:** Empty `stripe_secret_key` enables direct subscription creation and raw JSON webhooks without Stripe accounts.

---

*See also: [README](README.md) · [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
