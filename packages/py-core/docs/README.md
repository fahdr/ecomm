# ecomm_core

> Part of [ecomm_core](README.md) documentation

**Shared core library for all ecomm SaaS platform services**

`ecomm_core` is a Python package that provides authentication, billing, database infrastructure, models, schemas, health checks, and test utilities for the 8 SaaS services in the ecomm platform. It eliminates ~7,000 lines of duplicated code and ensures consistent behavior across TrendScout, ContentForge, RankPilot, FlowSend, SpyDrop, PostPilot, AdScale, and ShopChat.

## Quick Start

```bash
# Install from monorepo root
pip install -e packages/py-core

# Install with dev dependencies
pip install -e "packages/py-core[dev]"
```

## What's Included

- **Authentication:** JWT tokens, password hashing, API key auth, FastAPI dependencies
- **Billing:** Stripe subscription management, checkout/portal sessions, webhook handling
- **Database:** Async SQLAlchemy engine and session factory utilities
- **Models:** User, Subscription, ApiKey base models with relationships
- **Schemas:** Pydantic request/response models for auth and billing
- **Routers:** Pluggable FastAPI routers for `/auth`, `/billing`, `/api-keys`, `/usage`, `/webhooks`, `/health`
- **Plans:** Plan tier definitions with resource limits
- **LLM Client:** Async client for the centralized LLM Gateway
- **Testing:** Pytest fixtures for database isolation and auth helpers
- **Middleware:** CORS setup utilities
- **Config:** Base configuration class with sensible defaults

## Core Metrics

- **Version:** 0.1.0
- **Tests:** 19 passing
- **Python:** 3.12+
- **Services using this package:** 8 (all SaaS services)
- **Lines of code eliminated:** ~7,000 (deduplicated across services)

## Documentation

- [Setup](SETUP.md) — Installation and integration patterns
- [Architecture](ARCHITECTURE.md) — Module design and extension points
- [API Reference](API_REFERENCE.md) — Complete API documentation
- [Testing](TESTING.md) — Test infrastructure and coverage

## Philosophy

This package follows these principles:

1. **No global state:** All factories accept settings/dependencies as parameters
2. **Service-agnostic:** Generic enough to support diverse use cases (ads, content, trends)
3. **Test-friendly:** Schema-based isolation, mock modes, helper fixtures
4. **Incremental adoption:** Services can use only what they need (e.g., auth without billing)

## License

Proprietary — part of the ecomm platform monorepo.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
