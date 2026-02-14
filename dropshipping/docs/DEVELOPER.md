# Developer Guide — Dropshipping Platform

The core dropshipping platform lives in `dropshipping/` and provides multi-tenant
store management, products, orders, fulfillment, and integration with 8 standalone
SaaS services via the ServiceBridge.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI | Latest |
| ORM | SQLAlchemy 2.0 (async) | 2.x |
| Database | PostgreSQL | 16 |
| Cache / Queue | Redis | 7 |
| Task Queue | Celery | 5.x |
| Migrations | Alembic | Latest |
| Dashboard | Next.js (App Router) | 16 |
| Storefront | Next.js (App Router) | 16 |
| Auth | JWT (python-jose) + bcrypt | -- |
| Billing | Stripe (mock mode supported) | -- |
| Testing | pytest + pytest-asyncio + httpx | -- |

---

## Local Development

```bash
# Backend API (port 8000)
cd dropshipping/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker
cd dropshipping/backend
celery -A app.tasks.celery_app worker -l info

# Dashboard (port 3000)
cd dropshipping/dashboard
npm run dev

# Storefront (port 3001)
cd dropshipping/storefront
npm run dev -- -p 3001
```

---

## ServiceBridge — Platform Event Integration

The ServiceBridge dispatches platform lifecycle events to connected SaaS services
via HMAC-signed HTTP webhooks through Celery background tasks.

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/tasks/bridge_tasks.py` | Celery task with `EVENT_SERVICE_MAP` |
| `backend/app/services/bridge_service.py` | HMAC signing, async query helpers |
| `backend/app/api/bridge.py` | REST API (5 endpoints) for dashboard |
| `backend/app/models/bridge_delivery.py` | `BridgeDelivery` ORM model |
| `backend/app/schemas/bridge.py` | Pydantic schemas |

### Event Dispatch Flow

1. API handler (e.g. `products.py`) calls `fire_platform_event()` after CRUD
2. `fire_platform_event()` lazy-imports and calls `dispatch_platform_event.delay()`
3. Celery task queries `ServiceIntegration` for connected services
4. Filters by `EVENT_SERVICE_MAP` (5 event types → service lists)
5. POSTs to each service with HMAC-SHA256 signature header
6. Records `BridgeDelivery` row for each attempt (success/failure, latency)

### Event → Service Mapping

| Event | Services |
|-------|---------|
| `product.created` | ContentForge, RankPilot, TrendScout, PostPilot, AdScale, ShopChat |
| `product.updated` | ContentForge, RankPilot, ShopChat |
| `order.created` | FlowSend, SpyDrop |
| `order.shipped` | FlowSend |
| `customer.created` | FlowSend |

### HMAC Signing

Events are signed with `platform_webhook_secret` (shared secret in config).
Services verify via `X-Platform-Signature` header using HMAC-SHA256.

### Bridge API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/bridge/activity` | GET | Paginated delivery log with filters |
| `/api/v1/bridge/activity/{type}/{id}` | GET | Per-resource deliveries |
| `/api/v1/bridge/service/{name}/activity` | GET | Per-service deliveries |
| `/api/v1/bridge/summary` | GET | 24h per-service summary |
| `/api/v1/bridge/dispatch` | POST | Manual event dispatch |

---

## Dashboard Components

### ServiceBridge UI

| Component | File | Purpose |
|-----------|------|---------|
| Service Activity Card | `components/service-activity-card.tsx` | Reusable delivery list widget |
| Resource Service Status | `components/resource-service-status.tsx` | 8-service status grid |
| Activity Page | `app/stores/[id]/services/activity/page.tsx` | Full activity log with KPIs |

---

## Testing

### Running Tests

```bash
cd dropshipping/backend
python -m pytest tests/ -v
```

### Test Isolation

Tests use schema-based isolation with the `dropshipping_test` PostgreSQL schema.
Raw asyncpg handles schema creation/termination. The `search_path` is set via
SQLAlchemy `connect` event listener.

### Test Counts

- **Total:** 580 tests
- **ServiceBridge:** 39 tests (`test_bridge_api.py`, `test_bridge_service.py`, `test_bridge_tasks.py`)
- **Core features:** 541 tests (auth, stores, products, orders, etc.)

---

## Background Tasks (Celery)

21 task functions across 7 modules:

| Module | Tasks | Purpose |
|--------|-------|---------|
| `bridge_tasks.py` | 1 | ServiceBridge event dispatch with HMAC |
| `email_tasks.py` | 9 | Transactional emails |
| `webhook_tasks.py` | 1 | Store webhook delivery |
| `notification_tasks.py` | 4 | Dashboard notifications |
| `fraud_tasks.py` | 1 | Fraud risk scoring |
| `order_tasks.py` | 3 | Order orchestration + auto-fulfill |
| `analytics_tasks.py` | 2 | Daily analytics + cleanup |
