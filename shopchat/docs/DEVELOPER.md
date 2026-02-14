# Developer Guide

**For Developers:** ShopChat is an AI Shopping Assistant service that provides an embeddable chat widget for e-commerce stores. It leverages Claude API integration with a knowledge base built from product catalogs, policy pages, and custom Q&A to answer customer questions, recommend products, and provide real-time support. The service includes chatbot configuration with personality styles, knowledge base management with plan-enforced limits, conversation tracking with satisfaction scoring, a public widget API for unauthenticated visitor chat, and analytics dashboards for monitoring chatbot performance.

---

## Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Backend API | FastAPI | Async, OpenAPI docs at `/docs` |
| ORM | SQLAlchemy 2.0 | Async via `asyncpg` driver |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Task Queue | Celery | Background jobs (embedding, analytics aggregation) |
| Dashboard | Next.js | 16, App Router |
| UI Framework | Tailwind CSS | Utility-first styling |
| Landing Page | Next.js | 16, static export |

---

## Local Development

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend API | `8108` | FastAPI server, Swagger docs at `http://localhost:8108/docs` |
| Dashboard | `3108` | Next.js dashboard UI |
| Landing Page | `3208` | Static marketing / landing page |
| PostgreSQL | `5508` | Database |
| Redis | `6408` | Cache and Celery broker |

### Quick Start

```bash
# Install dependencies, run migrations, and start all services
make install && make migrate && make start
```

### Access Points

- **API**: http://localhost:8108
- **API Docs (Swagger)**: http://localhost:8108/docs
- **Dashboard**: http://localhost:3108
- **Landing Page**: http://localhost:3208

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://...@db:5508/shopchat` |
| `DATABASE_URL_SYNC` | PostgreSQL sync connection string (Alembic) | `postgresql://...@db:5508/shopchat` |
| `REDIS_URL` | Redis connection string | `redis://redis:6408/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6408/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | `redis://redis:6408/2` |
| `SECRET_KEY` | JWT signing key | Set in `.env` |
| `STRIPE_SECRET_KEY` | Stripe API key (optional, mock mode if empty) | `""` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `""` |
| `NEXT_PUBLIC_API_URL` | Backend URL for the dashboard frontend | `http://localhost:8108` |

---

## Project Structure

```
shopchat/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route modules
│   │   │   ├── auth.py             # Registration, login, refresh, profile, provisioning
│   │   │   ├── chatbots.py         # Chatbot CRUD (POST, GET, PATCH, DELETE)
│   │   │   ├── knowledge.py        # Knowledge base CRUD with plan limit enforcement
│   │   │   ├── conversations.py    # List, detail, end, rate conversations
│   │   │   ├── widget.py           # Public endpoints (no auth): config + chat
│   │   │   ├── analytics.py        # Overview + per-chatbot analytics
│   │   │   ├── billing.py          # Plans, checkout, portal, subscription overview
│   │   │   ├── api_keys.py         # API key CRUD and revocation
│   │   │   ├── usage.py            # Cross-service usage reporting
│   │   │   ├── health.py           # Health check endpoint
│   │   │   ├── deps.py             # Dependency injection (auth, plan limits)
│   │   │   └── webhooks.py         # Stripe webhook handler
│   │   ├── constants/
│   │   │   └── plans.py            # Plan tier definitions and limits
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py             # User + PlanTier enum
│   │   │   ├── chatbot.py          # Chatbot (personality, widget_key, theme_config)
│   │   │   ├── knowledge_base.py   # Knowledge entries (source_type, content, metadata)
│   │   │   ├── conversation.py     # Conversations (visitor_id, status, satisfaction)
│   │   │   ├── message.py          # Messages (role: user/assistant, content)
│   │   │   ├── subscription.py     # Stripe subscription tracking
│   │   │   ├── api_key.py          # API key storage and scoping
│   │   │   └── base.py             # SQLAlchemy declarative Base
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/               # Business logic layer
│   │   │   ├── chatbot_service.py  # Chatbot CRUD + widget key generation
│   │   │   ├── knowledge_service.py# Knowledge CRUD + plan limit checks
│   │   │   ├── chat_service.py     # Conversation flow + AI response (mock)
│   │   │   ├── analytics_service.py# Aggregated analytics queries
│   │   │   ├── auth_service.py     # Registration, login, JWT, API key auth
│   │   │   └── billing_service.py  # Stripe integration + usage metrics
│   │   ├── tasks/                  # Celery background tasks
│   │   ├── utils/                  # Shared utilities
│   │   ├── config.py               # Settings from environment
│   │   ├── database.py             # Async engine + session factory
│   │   └── main.py                 # FastAPI app initialization
│   ├── tests/                      # 88 backend tests (pytest + httpx)
│   │   ├── conftest.py             # Fixtures: client, auth_headers, DB setup/teardown
│   │   ├── test_auth.py            # 10 auth tests
│   │   ├── test_chatbots.py        # 21 chatbot CRUD tests
│   │   ├── test_knowledge.py       # 26 knowledge base tests
│   │   ├── test_conversations.py   # 17 conversation tests
│   │   ├── test_widget.py          # 16 widget (public API) tests
│   │   ├── test_billing.py         # 9 billing tests
│   │   ├── test_api_keys.py        # 5 API key tests
│   │   └── test_health.py          # 1 health check test
│   ├── alembic/                    # Database migrations
│   └── requirements.txt
├── dashboard/
│   └── src/
│       ├── app/                    # Next.js App Router pages
│       │   ├── page.tsx            # Dashboard home
│       │   ├── chatbots/page.tsx   # Chatbot management
│       │   ├── knowledge/page.tsx  # Knowledge base management
│       │   ├── conversations/page.tsx # Conversation history
│       │   ├── billing/page.tsx    # Billing / subscription
│       │   ├── api-keys/page.tsx   # API key management
│       │   ├── settings/page.tsx   # Account settings
│       │   ├── login/page.tsx      # Login page
│       │   └── register/page.tsx   # Registration page
│       └── service.config.ts       # Service branding, navigation, plan tiers
├── landing/                        # Static landing page (Next.js)
├── scripts/                        # Utility scripts
├── docker-compose.yml              # Local dev orchestration
├── Makefile                        # Build, test, and run targets
└── README.md                       # Service overview
```

---

## Testing

ShopChat has **88 backend tests** -- the highest test count tied with FlowSend across all services.

### Running Tests

```bash
# Run all backend tests
make test-backend

# Run with verbose output
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_chatbots.py -v

# Run a single test
cd backend && pytest tests/test_widget.py::test_widget_chat_basic -v
```

### Test Distribution

| Test File | Count | What It Covers |
|-----------|-------|---------------|
| `test_chatbots.py` | 21 | CRUD, user scoping, widget key uniqueness, validation |
| `test_knowledge.py` | 26 | CRUD, plan limits, chatbot ownership, source types, scoping |
| `test_conversations.py` | 17 | List, detail with messages, end, rate, pagination, scoping |
| `test_widget.py` | 16 | Public config, chat flow, AI responses, knowledge base context, product suggestions |
| `test_auth.py` | 10 | Register, login, refresh, profile, duplicate email, invalid credentials |
| `test_billing.py` | 9 | Plans, checkout, portal, billing overview, subscriptions |
| `test_api_keys.py` | 5 | Create, list, revoke, auth via API key |
| `test_health.py` | 1 | Health check endpoint |

### Test Fixtures

Tests use a shared `conftest.py` with these key fixtures:

- **`client`**: `httpx.AsyncClient` configured for the FastAPI app.
- **`auth_headers`**: Pre-registered user with `Authorization: Bearer <token>` headers.
- **`register_and_login(client, email)`**: Helper to create a new user and return auth headers.
- **`setup_db`**: Auto-use fixture that creates tables before tests and truncates all tables with `CASCADE` between tests. Terminates non-self database connections to prevent deadlocks.

---

## API Conventions

- **Base path**: `/api/v1/`
- **Auth**: JWT Bearer token via `Authorization: Bearer <token>` header. Some endpoints also accept `X-API-Key` header.
- **Public endpoints**: Widget endpoints (`/api/v1/widget/*`) require no authentication; they use the `widget_key` to identify the chatbot.
- **Pagination**: All list endpoints return `{ items: [...], total, page, page_size }`.
- **Error responses**: Standard HTTP status codes with `{ "detail": "..." }` body.
- **204 No Content**: DELETE endpoints return 204 with no response body. The frontend must check `response.status === 204` before calling `.json()`.
- **Plan enforcement**: Knowledge base creation returns 403 when the plan limit is reached. Widget chat returns 429 when the monthly conversation limit is reached.
- **Sentinel pattern**: Update endpoints use Python `...` (Ellipsis) as a sentinel value to distinguish "field not provided" from explicit `None` in optional fields like `metadata`.

---

## Design System

| Element | Value |
|---------|-------|
| Primary Color | Indigo -- `oklch(0.55 0.20 275)` / `#6366f1` |
| Accent Color | Light Indigo -- `oklch(0.70 0.18 290)` / `#818cf8` |
| Heading Font | Outfit (conversational, friendly) |
| Body Font | Lexend |

The design system is configured in `dashboard/src/service.config.ts` and drives all sidebar navigation, plan cards, and branding across the dashboard.

---

## Key Design Decisions

### 1. Embeddable Widget Architecture

The widget is a vanilla JS snippet with no framework dependency. It communicates with the backend via public endpoints that use the `widget_key` for identification instead of JWT authentication. This means:
- Store owners embed a single `<script>` tag.
- Visitors chat immediately without login.
- The widget authenticates via the `widget_key` parameter in every request.
- Rate limiting should be applied in production to prevent abuse of public endpoints.

### 2. Knowledge Base RAG Pattern

Knowledge base entries are categorized by `source_type` (`product_catalog`, `policy_page`, `faq`, `custom_text`, `url`). During chat, the service:
1. Retrieves all active entries for the chatbot.
2. Performs keyword-based search to find the top 3 relevant entries.
3. Feeds the matched content as context to the AI response generator.
4. Returns product suggestions when catalog entries match.

The current AI response is a mock implementation. Replace `_generate_ai_response()` in `chat_service.py` with actual Claude API calls for production.

### 3. Conversation Context and Lifecycle

Conversations are created automatically when a visitor sends their first message. Subsequent messages from the same `visitor_id` are grouped into the same active conversation. The lifecycle is:
- **active**: Visitor is chatting; messages are being exchanged.
- **ended**: Conversation manually ended via API or by timeout.
- Satisfaction scores (1.0-5.0) can be set on any conversation.

### 4. Multi-Tenant User Scoping

All queries are scoped to the authenticated user. Chatbot CRUD, knowledge base entries, conversations, and analytics are all filtered by `user_id` through the chatbot ownership chain (`user -> chatbot -> knowledge_base / conversation -> message`). Cross-user access returns 404 (not 403) to avoid leaking information about resource existence.

### 5. Plan Limit Enforcement

Plan limits are defined in `constants/plans.py`:
- `max_items`: Monthly conversation limit (50 free, 1000 pro, unlimited enterprise).
- `max_secondary`: Knowledge base page limit (10 free, 500 pro, unlimited enterprise).

Limits are checked via dependency injection before resource creation. The widget chat endpoint enforces conversation limits by looking up the chatbot owner's plan.

---

## Platform Event Webhook

### Platform Event Webhook

Each service receives platform events from the dropshipping backend via
`POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed
using `platform_webhook_secret`. The receiver verifies the signature and
routes events to service-specific handlers.
