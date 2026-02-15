# ShopChat Architecture

> Part of [ShopChat](README.md) documentation

This document describes the technical architecture, design decisions, and system structure for the ShopChat AI Shopping Assistant service.

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
│   ├── tests/                      # 113 backend tests (pytest + httpx)
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

## Database Schema

### Core Tables

#### users
```sql
id                    UUID PRIMARY KEY
email                 VARCHAR(255) UNIQUE NOT NULL
password_hash         VARCHAR(255) NOT NULL
plan                  VARCHAR(50) DEFAULT 'free'
stripe_customer_id    VARCHAR(255) NULL
external_platform_id  VARCHAR(255) NULL
external_store_id     VARCHAR(255) NULL
created_at            TIMESTAMP DEFAULT now()
updated_at            TIMESTAMP DEFAULT now()
```

#### chatbots
```sql
id                UUID PRIMARY KEY
user_id           UUID REFERENCES users(id) ON DELETE CASCADE
name              VARCHAR(255) NOT NULL
personality       VARCHAR(50) DEFAULT 'friendly'
welcome_message   TEXT DEFAULT 'Hi there! How can I help you today?'
theme_config      JSONB DEFAULT '{"primary_color": "#6366f1", ...}'
is_active         BOOLEAN DEFAULT true
widget_key        VARCHAR(64) UNIQUE
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

#### knowledge_base
```sql
id            UUID PRIMARY KEY
chatbot_id    UUID REFERENCES chatbots(id) ON DELETE CASCADE
source_type   VARCHAR(50) DEFAULT 'custom_text'
title         VARCHAR(500) NOT NULL
content       TEXT NOT NULL
metadata      JSONB NULL
is_active     BOOLEAN DEFAULT true
created_at    TIMESTAMP
updated_at    TIMESTAMP
```

#### conversations
```sql
id                   UUID PRIMARY KEY
chatbot_id           UUID REFERENCES chatbots(id) ON DELETE CASCADE
visitor_id           VARCHAR(255)
visitor_name         VARCHAR(255) NULL
started_at           TIMESTAMP DEFAULT now()
ended_at             TIMESTAMP NULL
message_count        INTEGER DEFAULT 0
satisfaction_score   FLOAT NULL
status               VARCHAR(50) DEFAULT 'active'
```

#### messages
```sql
id                UUID PRIMARY KEY
conversation_id   UUID REFERENCES conversations(id) ON DELETE CASCADE
role              VARCHAR(20)  -- 'user' or 'assistant'
content           TEXT
metadata          JSONB NULL
created_at        TIMESTAMP
```

### Billing Tables

#### subscriptions
```sql
id                    UUID PRIMARY KEY
user_id               UUID REFERENCES users(id) ON DELETE CASCADE
stripe_subscription_id VARCHAR(255) UNIQUE
plan                  VARCHAR(50)
status                VARCHAR(50)
current_period_start  TIMESTAMP
current_period_end    TIMESTAMP
cancel_at_period_end  BOOLEAN
created_at            TIMESTAMP
updated_at            TIMESTAMP
```

#### api_keys
```sql
id          UUID PRIMARY KEY
user_id     UUID REFERENCES users(id) ON DELETE CASCADE
key_prefix  VARCHAR(20)
key_hash    VARCHAR(255)
name        VARCHAR(255)
is_active   BOOLEAN DEFAULT true
last_used   TIMESTAMP NULL
created_at  TIMESTAMP
```

---

## Key Design Decisions

### 1. Embeddable Widget Architecture

The widget is a vanilla JS snippet with no framework dependency. It communicates with the backend via public endpoints that use the `widget_key` for identification instead of JWT authentication. This means:

- Store owners embed a single `<script>` tag
- Visitors chat immediately without login
- The widget authenticates via the `widget_key` parameter in every request
- Rate limiting should be applied in production to prevent abuse of public endpoints

**Why this approach:**
- No build step or framework version conflicts with the host site
- Works on any website (Shopify, WordPress, custom HTML)
- Visitors don't need ShopChat accounts to use the widget
- Reduces friction for store owners and customers

### 2. Knowledge Base RAG Pattern

Knowledge base entries are categorized by `source_type` (`product_catalog`, `policy_page`, `faq`, `custom_text`, `url`). During chat, the service:

1. Retrieves all active entries for the chatbot
2. Performs keyword-based search to find the top 3 relevant entries
3. Feeds the matched content as context to the AI response generator
4. Returns product suggestions when catalog entries match

**Current implementation:**
- Keyword matching ranks entries by query word overlap
- Top 3 entries are passed as context
- AI response is a mock implementation (see Production Considerations below)

**Future improvements:**
- Vector embeddings for semantic search
- Re-ranking based on conversation history
- User feedback loop to improve relevance

### 3. Conversation Context and Lifecycle

Conversations are created automatically when a visitor sends their first message. Subsequent messages from the same `visitor_id` are grouped into the same active conversation. The lifecycle is:

- **active**: Visitor is chatting; messages are being exchanged
- **ended**: Conversation manually ended via API or by timeout
- Satisfaction scores (1.0-5.0) can be set on any conversation

**Why this approach:**
- Visitors don't need to explicitly "start" a conversation
- The `visitor_id` acts as a session identifier (typically a client-side UUID)
- Store owners can review full conversation threads
- Satisfaction scores provide quality metrics for analytics

### 4. Multi-Tenant User Scoping

All queries are scoped to the authenticated user. Chatbot CRUD, knowledge base entries, conversations, and analytics are all filtered by `user_id` through the chatbot ownership chain:

```
user -> chatbot -> knowledge_base
user -> chatbot -> conversation -> message
```

**Security guarantees:**
- Cross-user access returns 404 (not 403) to avoid leaking information about resource existence
- Widget endpoints (public) use the widget_key to identify the chatbot and infer ownership
- Database queries join through the ownership chain to enforce scoping

### 5. Plan Limit Enforcement

Plan limits are defined in `constants/plans.py`:

| Tier | `max_items` (conversations/mo) | `max_secondary` (knowledge pages) |
|------|-------------------------------|----------------------------------|
| Free | 50 | 10 |
| Pro | 1,000 | 500 |
| Enterprise | -1 (unlimited) | -1 (unlimited) |

Limits are checked via dependency injection before resource creation:
- Knowledge base creation returns 403 when `max_secondary` is exceeded
- Widget chat returns 429 when `max_items` is exceeded

**Counting logic:**
- Knowledge base: Total count across all user's chatbots
- Conversations: Monthly count from the first of the current month

### 6. Widget Key Generation

Widget keys are generated using `secrets.token_urlsafe(24)` with the prefix `wk_`. They are:
- Unique across all chatbots (enforced by unique constraint)
- URL-safe (no special characters)
- Unpredictable (cryptographically random)

**Example:** `wk_Xg7kP2mNzQ8vRtY5wLhJ9cFnB1aD`

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
| Primary Color | Indigo – `oklch(0.55 0.20 275)` / `#6366f1` |
| Accent Color | Light Indigo – `oklch(0.70 0.18 290)` / `#818cf8` |
| Heading Font | Outfit (conversational, friendly) |
| Body Font | Lexend |

The design system is configured in `dashboard/src/service.config.ts` and drives all sidebar navigation, plan cards, and branding across the dashboard.

---

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Event types:**
- `user.created`: Provision a new user in the service
- `user.deleted`: Clean up user data
- `subscription.updated`: Sync plan tier changes
- `store.connected`: Link store to user account

---

## Production Considerations

### 1. AI Response Generation

The current implementation uses a mock AI response (`_generate_ai_response()` in `chat_service.py`). Production deployment requires:
- Claude API integration via the LLM Gateway microservice
- Proper prompt engineering with system messages
- Guardrails and content safety filters
- Token usage tracking for billing

### 2. Rate Limiting

Public widget endpoints have no rate limiting in the current implementation. Production needs:
- Per-widget-key rate limits (e.g., 100 requests/minute)
- Per-visitor-id rate limits (e.g., 10 requests/minute)
- Redis-based rate limiting with sliding windows

### 3. Vector Embeddings

Current keyword search is O(n) per query. For large knowledge bases (1000+ entries), implement:
- Vector embeddings stored in PostgreSQL (pgvector extension) or dedicated vector DB
- Semantic search using cosine similarity
- Background Celery task to generate embeddings on entry creation

### 4. Stripe Integration

Currently uses mock mode for testing. Production requires:
- Stripe Price IDs configured via environment variables
- Webhook endpoint verification with `STRIPE_WEBHOOK_SECRET`
- Idempotency keys for all Stripe API calls
- Retry logic for failed payment events

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
