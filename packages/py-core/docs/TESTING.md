# Testing Guide

> Part of [ecomm_core](README.md) documentation

Test infrastructure, running tests, and coverage details for the `ecomm_core` package.

## Test Stack

- **Framework:** pytest with pytest-asyncio
- **HTTP Client:** httpx AsyncClient
- **Database:** PostgreSQL with async SQLAlchemy
- **Isolation:** Schema-based test isolation (no cross-contamination)

## Running Tests

```bash
# From package root
cd packages/py-core
pytest              # all tests
pytest -v           # verbose
pytest tests/test_core.py::TestPasswordHashing::test_hash_and_verify  # specific test
pytest --cov=ecomm_core --cov-report=html  # with coverage

# From monorepo root
pytest packages/py-core/tests/
make test           # all services including py-core
```

## Test Organization

```
tests/
├── __init__.py
└── test_core.py          # 19 tests covering core functionality
```

## Test Coverage by Module

| Module | Tests | Coverage |
|--------|-------|----------|
| `auth.service` | 6 | Password hashing, JWT creation/decoding |
| `config` | 2 | Config defaults, CORS origins parsing |
| `plans` | 2 | Plan limits creation, price ID resolution |
| `models` | 4 | Table names, enum values, importability |
| `schemas` | 3 | Validation rules, default values |
| `health` | 1 | Health router creation |
| `llm_client` | 1 | Mock client response format |
| **Total** | **19** | **Core functionality verified** |

## Key Test Patterns

- **Password hashing:** Verify bcrypt round-trips and different salts per hash
- **JWT tokens:** Verify create/decode round-trip, check payload fields (`sub`, `type`)
- **Config:** Verify CORS origins string parses to list
- **Schema validation:** Verify short passwords are rejected by `RegisterRequest`

## Integration Testing in Services

Services use `ecomm_core.testing` utilities. Standard fixture setup:

1. `create_tables` (session-scoped) -- creates schema + tables, drops on teardown
2. `client` -- httpx `AsyncClient` bound to the FastAPI app
3. `auth_headers` -- calls `register_and_login(client)` for authenticated requests

## Schema-Based Isolation Pattern

**Problem:** All services share one PostgreSQL database. Using `pg_terminate_backend` in tests killed connections from other services running in parallel.

**Solution:** Each service gets a dedicated schema (e.g., `trendscout_test`). Tables are created in the service's schema, and `search_path` is set via SQLAlchemy `connect` event listener.

**Key fixtures:**
- `create_tables` (session-scoped): Creates schema with raw asyncpg, then `Base.metadata.create_all`
- `db_session` (per-test): Yields session, truncates all tables after each test for isolation

## Mock Mode Testing

**Stripe Mock Mode** (when `stripe_secret_key` is empty):
- Subscriptions created directly without Stripe API calls
- Webhooks accept raw JSON without signature verification
- Customer/subscription IDs prefixed with `mock_`

**LLM Mock Client:** Use `call_llm_mock()` instead of `call_llm()` -- returns deterministic responses with `provider="mock"` and `cost_usd=0.0`.

## Coverage Goals

- **Current:** 19 core tests covering foundational functionality
- **Service Tests:** Each of the 8 services has 100+ tests using `ecomm_core`
- **Integration Coverage:** Auth, billing, webhooks, and API keys tested in service contexts

## Running Service Tests

```bash
pytest trendscout/backend/tests/    # 158 tests
pytest contentforge/backend/tests/  # 116 tests
make test                           # all services
```

## Common Test Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Connection errors | PostgreSQL not running | `docker-compose up -d db` |
| Tests pass alone, fail in parallel | Missing schema isolation | Verify `search_path` is set correctly |
| JWT decode returns None | Secret key mismatch | Use same secret in create and decode |
| Pydantic validation errors | Schema changes | Update test data to match current rules |

## Future Improvements

- Database integration tests (User CRUD, Subscription sync)
- Router integration tests (auth, billing endpoints)
- API key authentication and provisioning workflow tests
- Increase from 19 to 50+ tests

---

*See also: [README](README.md) · [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
