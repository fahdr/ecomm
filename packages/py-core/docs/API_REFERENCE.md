# API Reference

> Part of [ecomm_core](README.md) documentation

Complete reference of all exported modules, classes, functions, and decorators in `ecomm_core`.

## Module: `ecomm_core.auth.service`

Authentication service for JWT tokens, password management, and user operations.

| Function | Parameters | Returns |
|----------|-----------|---------|
| `hash_password(password)` | Plain text password | Bcrypt hash string |
| `verify_password(plain_password, hashed_password)` | Plain + hashed passwords | `bool` |
| `create_access_token(user_id, *, secret_key, algorithm="HS256", expire_minutes=15)` | User UUID + signing config | JWT string |
| `create_refresh_token(user_id, *, secret_key, algorithm="HS256", expire_days=7)` | User UUID + signing config | JWT string |
| `decode_token(token, *, secret_key, algorithm="HS256")` | JWT string + secret | Payload dict or `None` |
| `register_user(db, email, password)` | Session, email, password | `User` (raises `ValueError` if duplicate) |
| `authenticate_user(db, email, password)` | Session, email, password | `User` or `None` |
| `get_user_by_id(db, user_id)` | Session, UUID | `User` or `None` |
| `provision_user(db, email, password, plan, external_platform_id, external_store_id=None, *, service_name="svc")` | Platform provisioning data | `tuple[User, api_key_string]` |
| `get_user_by_api_key(db, raw_key)` | Session, raw API key | `User` or `None` |

## Module: `ecomm_core.auth.deps`

FastAPI dependency factories for authentication.

| Function | Parameters | Returns |
|----------|-----------|---------|
| `create_get_current_user(get_db)` | Service's `get_db` dependency | FastAPI dependency for JWT auth |
| `create_get_current_user_or_api_key(get_db)` | Service's `get_db` dependency | FastAPI dependency for JWT or API key auth |

## Module: `ecomm_core.auth.router`

| Function | Returns |
|----------|---------|
| `create_auth_router(get_db, get_current_user, get_current_user_or_api_key)` | APIRouter with auth endpoints |

**Endpoints:** `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/provision`

## Module: `ecomm_core.billing.service`

Billing service for Stripe subscription management. When `stripe_secret_key` is empty, operates in mock mode.

| Function | Returns | Notes |
|----------|---------|-------|
| `get_or_create_stripe_customer(db, user, *, stripe_secret_key, service_name)` | Stripe Customer ID string | |
| `create_subscription_checkout(db, user, plan, plan_limits, *, stripe_secret_key, success_url, cancel_url, service_name)` | `{session_id, checkout_url}` | Raises `ValueError` if plan is free or user has active sub |
| `create_portal_session(db, user, *, stripe_secret_key, success_url)` | `{portal_url}` | Raises `ValueError` if no Stripe customer |
| `sync_subscription_from_event(db, event_data, plan_limits)` | `Subscription` or `None` | Upserts from Stripe webhook |
| `get_subscription(db, user_id)` | `Subscription` or `None` | |
| `get_billing_overview(db, user, plan_limits)` | Dict with plan, subscription, usage | |
| `get_usage(db, user, plan_limits)` | Dict with plan, period, metrics | Template -- services override |

## Module: `ecomm_core.billing.router`

| Function | Returns |
|----------|---------|
| `create_billing_router(get_db, get_current_user, plan_limits)` | APIRouter with billing endpoints |

**Endpoints:** `GET /billing/plans` (public), `POST /billing/checkout`, `POST /billing/portal`, `GET /billing/current`, `GET /billing/overview`

## Module: `ecomm_core.billing.webhooks`

| Function | Returns |
|----------|---------|
| `create_webhook_router(session_factory, plan_limits)` | APIRouter with `POST /webhooks/stripe` |

Note: Accepts `session_factory` (not `get_db`) because webhooks run outside request context.

## Module: `ecomm_core.db`

| Function | Parameters | Returns |
|----------|-----------|---------|
| `create_db_engine(database_url, echo=False)` | Async PostgreSQL URL | AsyncEngine |
| `create_session_factory(engine)` | AsyncEngine | `async_sessionmaker` |
| `create_get_db(session_factory)` | Session factory | FastAPI `Depends()` generator |

## Module: `ecomm_core.models`

### PlanTier (Enum)

Values: `free`, `pro`, `enterprise`

### User

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `email` | str | Unique, indexed |
| `hashed_password` | str | Bcrypt |
| `is_active` | bool | Account status |
| `plan` | PlanTier | Current tier |
| `stripe_customer_id` | str? | Stripe Customer ID |
| `external_platform_id` | str? | Dropshipping platform user ID |
| `external_store_id` | str? | Dropshipping platform store ID |
| `created_at` / `updated_at` | datetime | Timestamps |

Relationships: `subscription` (one), `api_keys` (many)

### SubscriptionStatus (Enum)

Values: `active`, `trialing`, `past_due`, `canceled`, `unpaid`, `incomplete`

### Subscription

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to User |
| `stripe_subscription_id` | str | Stripe's ID |
| `stripe_price_id` | str | Stripe Price ID |
| `plan` | PlanTier | Tier |
| `status` | SubscriptionStatus | Current status |
| `current_period_start` / `current_period_end` | datetime | Billing period |
| `cancel_at_period_end` | bool | Cancellation scheduled |
| `trial_start` / `trial_end` | datetime? | Trial dates |

### ApiKey

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK to User |
| `name` | str | Human-readable label |
| `key_hash` | str | SHA-256 hash |
| `key_prefix` | str | First 12 chars |
| `scopes` | list[str] | Permission scopes |
| `is_active` | bool | Active status |
| `last_used_at` | datetime? | Last usage |
| `expires_at` | datetime? | Optional expiration |

## Module: `ecomm_core.plans`

### PlanLimits (dataclass)

Attributes: `max_items` (-1 = unlimited), `max_secondary`, `price_monthly_cents`, `stripe_price_id`, `trial_days`, `api_access`

| Function | Returns |
|----------|---------|
| `create_default_plan_limits(free_items=10, free_secondary=25, pro_items=100, pro_secondary=500, pro_price_cents=2900, enterprise_price_cents=9900)` | `dict[PlanTier, PlanLimits]` |
| `init_price_ids(plan_limits, pro_price_id, enterprise_price_id)` | Updated plan limits with Stripe IDs |
| `resolve_plan_from_price_id(plan_limits, price_id)` | `PlanTier` or `None` |

## Module: `ecomm_core.health`

| Function | Returns |
|----------|---------|
| `create_health_router(service_name)` | APIRouter with `GET /health` |

## Module: `ecomm_core.api_keys_router`

| Function | Returns |
|----------|---------|
| `create_api_keys_router(get_db, get_current_user)` | APIRouter with API key CRUD |

**Endpoints:** `POST /api-keys` (returns raw key once), `GET /api-keys` (list, no raw keys), `DELETE /api-keys/{key_id}` (revoke)

## Module: `ecomm_core.usage_router`

| Function | Returns |
|----------|---------|
| `create_usage_router(get_db, get_current_user_or_api_key, get_usage_fn)` | APIRouter with `GET /usage` |

`get_usage_fn` is an async function `(db, user) -> dict` that services override for specific metrics.

## Module: `ecomm_core.llm_client`

| Function | Returns |
|----------|---------|
| `call_llm(prompt, *, system, user_id, service_name, task_type, max_tokens, temperature, json_mode, gateway_url, gateway_key, timeout)` | Dict with `content`, `provider`, `model`, token counts, `cost_usd`, `cached`, `latency_ms` |
| `call_llm_mock(prompt, *, content="Mock LLM response for testing.", **kwargs)` | Dict mimicking gateway response format |

## Module: `ecomm_core.middleware`

| Function | Parameters |
|----------|-----------|
| `setup_cors(app, cors_origins)` | FastAPI app + list of origin strings |

## Module: `ecomm_core.config`

### BaseServiceConfig (BaseSettings)

Key attributes: `service_name`, `database_url`, `redis_url`, `jwt_secret_key`, `stripe_secret_key` (empty = mock mode), `llm_gateway_url`, `cors_origins` (comma-separated string).

Property: `cors_origins_list` -- parsed list of CORS origins.

Services subclass and add custom fields.

## Module: `ecomm_core.testing`

| Function | Returns |
|----------|---------|
| `create_test_engine(database_url)` | AsyncEngine with NullPool |
| `create_test_session_factory(engine)` | Test session factory |
| `register_and_login(client, email=None)` | Dict with `Authorization` header |

---

*See also: [README](README.md) · [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
