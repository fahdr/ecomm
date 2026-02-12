# Implementation Steps

This document records the implementation steps taken to build the ShopChat AI Shopping Assistant service, from initial scaffolding through models, services, routes, tests, dashboard pages, and landing page.

---

## Step 1: Template Scaffolding

ShopChat was scaffolded from the shared service template using `scripts/create-service.sh`. The scaffold script performs placeholder replacement across the entire service directory:

| Placeholder | Value |
|-------------|-------|
| `{{SERVICE_NAME}}` | ShopChat |
| `{{SERVICE_SLUG}}` | shopchat |
| `{{SERVICE_TAGLINE}}` | AI Shopping Assistant |
| `{{BACKEND_PORT}}` | 8108 |
| `{{DASHBOARD_PORT}}` | 3108 |
| `{{LANDING_PORT}}` | 3208 |
| `{{DB_PORT}}` | 5508 |
| `{{REDIS_PORT}}` | 6408 |
| `{{PRIMARY_COLOR_OKLCH}}` | oklch(0.55 0.20 275) |
| `{{PRIMARY_COLOR_HEX}}` | #6366f1 |
| `{{ACCENT_COLOR_OKLCH}}` | oklch(0.70 0.18 290) |
| `{{ACCENT_COLOR_HEX}}` | #818cf8 |
| `{{HEADING_FONT}}` | Outfit |
| `{{BODY_FONT}}` | Inter |

**Files generated from template:**
- `backend/` -- FastAPI app skeleton with auth, billing, health, API keys, usage, webhooks
- `dashboard/` -- Next.js 16 App Router with login, register, billing, API keys, settings pages
- `landing/` -- Static landing page
- `docker-compose.yml` -- PostgreSQL 16, Redis 7, backend, dashboard, landing
- `Makefile` -- Build, test, start, migrate targets
- `README.md` -- Service overview

**What the template provides out of the box:**
- User authentication (register, login, refresh, profile)
- JWT + API key dual-auth dependency injection
- Stripe billing integration (plans, checkout, portal, webhooks)
- API key management (create, list, revoke)
- Usage reporting endpoint
- Health check endpoint
- Database migrations (Alembic)
- Test fixtures (conftest.py with async client, auth helpers, DB setup/teardown)
- Dashboard with auth pages, billing page, API keys page, settings page

---

## Step 2: Domain Models

Four service-specific SQLAlchemy models were created in `backend/app/models/`:

### 2a. Chatbot Model (`chatbot.py`)

```
Table: chatbots
Columns:
  - id: UUID (PK, default uuid4)
  - user_id: UUID (FK -> users.id, CASCADE, indexed)
  - name: String(255), NOT NULL
  - personality: String(50), default "friendly"
  - welcome_message: Text, default "Hi there! How can I help you today?"
  - theme_config: JSON, default {"primary_color": "#6366f1", "text_color": "#ffffff", "position": "bottom-right", "size": "medium"}
  - is_active: Boolean, default True
  - widget_key: String(64), UNIQUE, indexed
  - created_at: DateTime, server_default now()
  - updated_at: DateTime, server_default now(), onupdate now()
Relationships:
  - owner -> User (selectin)
  - knowledge_entries -> KnowledgeBase (cascade all, delete-orphan, selectin)
  - conversations -> Conversation (cascade all, delete-orphan, selectin)
```

### 2b. KnowledgeBase Model (`knowledge_base.py`)

```
Table: knowledge_base
Columns:
  - id: UUID (PK)
  - chatbot_id: UUID (FK -> chatbots.id, CASCADE, indexed)
  - source_type: String(50), default "custom_text"
  - title: String(500), NOT NULL
  - content: Text, NOT NULL
  - metadata: JSON, nullable
  - is_active: Boolean, default True
  - created_at, updated_at: DateTime
Relationships:
  - chatbot -> Chatbot
```

### 2c. Conversation Model (`conversation.py`)

```
Table: conversations
Columns:
  - id: UUID (PK)
  - chatbot_id: UUID (FK -> chatbots.id, CASCADE, indexed)
  - visitor_id: String(255), indexed
  - visitor_name: String(255), nullable
  - started_at: DateTime, server_default now()
  - ended_at: DateTime, nullable
  - message_count: Integer, default 0
  - satisfaction_score: Float, nullable
  - status: String(50), default "active"
Relationships:
  - chatbot -> Chatbot
  - messages -> Message (cascade all, delete-orphan, selectin, ordered by created_at)
```

### 2d. Message Model (`message.py`)

```
Table: messages
Columns:
  - id: UUID (PK)
  - conversation_id: UUID (FK -> conversations.id, CASCADE, indexed)
  - role: String(20) -- "user" or "assistant"
  - content: Text
  - metadata: JSON, nullable (product suggestions, links)
  - created_at: DateTime
Relationships:
  - conversation -> Conversation
```

### 2e. Alembic Migration

After defining models, a migration was generated and applied:

```bash
cd backend && alembic revision --autogenerate -m "add chatbots, knowledge_base, conversations, messages"
cd backend && alembic upgrade head
```

---

## Step 3: Service Layer

Four service modules were created in `backend/app/services/`:

### 3a. Chatbot Service (`chatbot_service.py`)

- `generate_widget_key()` -- generates `wk_` + `secrets.token_urlsafe(24)` for unique, URL-safe widget keys.
- `create_chatbot(db, user, name, personality, welcome_message, theme_config)` -- creates chatbot with generated widget key.
- `get_chatbot_by_id(db, chatbot_id, user_id)` -- retrieves chatbot scoped to user.
- `get_chatbot_by_widget_key(db, widget_key)` -- retrieves chatbot by public widget key (no user scoping).
- `list_chatbots(db, user_id, page, page_size)` -- paginated list of user's chatbots.
- `update_chatbot(db, chatbot, ...)` -- partial update of chatbot fields.
- `delete_chatbot(db, chatbot)` -- deletes chatbot (cascades to knowledge, conversations, messages).
- `count_user_chatbots(db, user_id)` -- counts user's total chatbots.

### 3b. Knowledge Service (`knowledge_service.py`)

- `count_user_knowledge_entries(db, user_id)` -- counts entries across all user's chatbots (for plan enforcement).
- `check_knowledge_limit(db, user)` -- checks if user can create more entries based on plan's `max_secondary`.
- `create_knowledge_entry(db, chatbot_id, source_type, title, content, metadata)` -- creates entry.
- `get_knowledge_entry(db, entry_id)` -- retrieves entry by ID.
- `list_knowledge_entries(db, chatbot_id, page, page_size)` -- paginated list for a chatbot.
- `list_all_user_knowledge_entries(db, user_id, page, page_size)` -- paginated list across all user's chatbots.
- `update_knowledge_entry(db, entry, ...)` -- partial update using Ellipsis sentinel for metadata.
- `delete_knowledge_entry(db, entry)` -- deletes entry.
- `get_active_entries_for_chatbot(db, chatbot_id)` -- retrieves all active entries for AI context building.

### 3c. Chat Service (`chat_service.py`)

- `count_monthly_conversations(db, user_id)` -- counts conversations since the first of the current month.
- `check_conversation_limit(db, user)` -- checks plan's `max_items` against monthly count.
- `get_or_create_conversation(db, chatbot, visitor_id, visitor_name)` -- finds active conversation or creates new one.
- `add_message(db, conversation, role, content, metadata)` -- adds message and increments `message_count`.
- `_search_knowledge_base(entries, query)` -- keyword-based search ranking entries by query word matches, returns top 3.
- `_generate_ai_response(chatbot, message, relevant_entries)` -- mock AI response with personality prefixes and knowledge base context. Returns (response_text, product_suggestions).
- `process_chat_message(db, chatbot, visitor_id, message_text, visitor_name)` -- main chat flow: get/create conversation, save user message, search knowledge base, generate AI response, save assistant message. Returns (conversation, ai_message, response_text, product_suggestions).
- `end_conversation(db, conversation)` -- sets status to "ended", records `ended_at`.
- `rate_conversation(db, conversation, score)` -- sets `satisfaction_score` on conversation.

### 3d. Analytics Service (`analytics_service.py`)

- `get_overview_analytics(db, user_id)` -- computes: total_conversations, total_messages, avg_satisfaction (excluding nulls), active_chatbots, conversations_today, top_chatbot_name.
- `get_chatbot_analytics(db, user_id)` -- per-chatbot breakdown: conversation count, message count, avg satisfaction, avg messages per conversation.

---

## Step 4: API Routes

Four service-specific route modules were created in `backend/app/api/`:

### 4a. Chatbots (`chatbots.py`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/chatbots` | `create_chatbot_endpoint` | JWT |
| GET | `/chatbots` | `list_chatbots_endpoint` | JWT |
| GET | `/chatbots/{chatbot_id}` | `get_chatbot_endpoint` | JWT |
| PATCH | `/chatbots/{chatbot_id}` | `update_chatbot_endpoint` | JWT |
| DELETE | `/chatbots/{chatbot_id}` | `delete_chatbot_endpoint` | JWT |

### 4b. Knowledge Base (`knowledge.py`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/knowledge` | `create_knowledge_entry_endpoint` | JWT |
| GET | `/knowledge` | `list_knowledge_entries_endpoint` | JWT |
| GET | `/knowledge/{entry_id}` | `get_knowledge_entry_endpoint` | JWT |
| PATCH | `/knowledge/{entry_id}` | `update_knowledge_entry_endpoint` | JWT |
| DELETE | `/knowledge/{entry_id}` | `delete_knowledge_entry_endpoint` | JWT |

Key behavior: ownership is verified by checking that the entry's chatbot belongs to the authenticated user. Plan limits are enforced on creation (403 if exceeded).

### 4c. Conversations (`conversations.py`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/conversations` | `list_conversations_endpoint` | JWT |
| GET | `/conversations/{conversation_id}` | `get_conversation_endpoint` | JWT |
| POST | `/conversations/{conversation_id}/end` | `end_conversation_endpoint` | JWT |
| POST | `/conversations/{conversation_id}/rate` | `rate_conversation_endpoint` | JWT |

Key behavior: conversations are listed by joining through the chatbot ownership chain (`Conversation -> Chatbot -> User`).

### 4d. Widget (`widget.py`) -- PUBLIC endpoints

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/widget/config/{widget_key}` | `get_widget_config` | None |
| POST | `/widget/chat` | `widget_chat` | None |

Key behavior: no JWT or API key required. The widget_key identifies the chatbot. Inactive chatbots return 404. Conversation limits are enforced by looking up the chatbot owner's plan.

### 4e. Analytics (`analytics.py`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/analytics/overview` | `get_analytics_overview` | JWT |
| GET | `/analytics/chatbots` | `get_per_chatbot_analytics` | JWT |

### 4f. Router Registration

All routers were registered in `backend/app/main.py` under the `/api/v1` prefix:

```python
app.include_router(chatbots.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(widget.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
```

---

## Step 5: Plan Limits Configuration

Plan limits were defined in `backend/app/constants/plans.py`:

```python
PLAN_LIMITS = {
    PlanTier.free: PlanLimits(
        max_items=50,          # 50 conversations/month
        max_secondary=10,      # 10 knowledge base pages
        price_monthly_cents=0,
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=1000,        # 1,000 conversations/month
        max_secondary=500,     # 500 knowledge base pages
        price_monthly_cents=1900,
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,          # Unlimited conversations
        max_secondary=-1,      # Unlimited knowledge base
        price_monthly_cents=7900,
        trial_days=14,
        api_access=True,
    ),
}
```

---

## Step 6: Pydantic Schemas

Request and response schemas were defined in `backend/app/schemas/chat.py`:

- `ChatbotCreate` -- name (min 1 char), personality, welcome_message, theme_config
- `ChatbotUpdate` -- all fields optional
- `ChatbotResponse` -- full chatbot with id, widget_key, timestamps
- `KnowledgeBaseCreate` -- chatbot_id, source_type, title (min 1), content (min 1), metadata
- `KnowledgeBaseUpdate` -- all fields optional
- `KnowledgeBaseResponse` -- full entry with id, timestamps
- `ConversationResponse` -- conversation fields without messages
- `ConversationDetailResponse` -- conversation with messages array
- `MessageResponse` -- id, role, content, metadata, created_at
- `SatisfactionRating` -- score (1.0-5.0, validated with ge/le)
- `ChatRequest` -- widget_key, visitor_id, message (min 1), visitor_name (optional)
- `ChatResponse` -- conversation_id, message, product_suggestions
- `ProductSuggestion` -- name, price, url
- `WidgetConfig` -- chatbot_name, personality, welcome_message, theme_config, is_active
- `AnalyticsOverview` -- total_conversations, total_messages, avg_satisfaction, active_chatbots, conversations_today, top_chatbot_name
- `ChatbotAnalytics` -- chatbot_id, chatbot_name, total_conversations, total_messages, avg_satisfaction, avg_messages_per_conversation
- `PaginatedResponse` -- items, total, page, page_size

---

## Step 7: Test Suite (88 tests)

Tests were written in `backend/tests/` using pytest-asyncio and httpx:

### 7a. `test_chatbots.py` (21 tests)

- Create: success, custom personality, theme config, no auth (401), empty name (422)
- List: empty, with data, pagination, user scoping
- Get: success, not found (404), other user (404)
- Update: name, personality, deactivate, theme config, not found, welcome message
- Delete: success (204), not found, other user, count decrement
- Widget key uniqueness

### 7b. `test_knowledge.py` (26 tests)

- Create: success, with metadata, no chatbot (404), other user's chatbot (404), no auth (401), empty title (422), empty content (422)
- List: empty, all entries, filter by chatbot, pagination, user scoping, nonexistent chatbot filter (404)
- Get: success, not found (404), other user (404)
- Update: title, content, source type, deactivate, metadata, not found, other user
- Delete: success (204), not found, other user, count decrement
- Source type variants: product_catalog, policy_page, faq, custom_text, url

### 7c. `test_conversations.py` (17 tests)

- List: empty, with data, filter by chatbot, pagination, user scoping
- Detail: success (with messages), not found, other user, message count increment
- End: success, already ended (400), not found
- Rate: success, boundaries (1.0, 5.0), too low (422), too high (422), not found, other user
- Response field validation

### 7d. `test_widget.py` (16 tests)

- Config: success, theme, invalid key (404), inactive chatbot (404), no auth required
- Chat: basic, creates conversation, continues conversation, different visitors, visitor name, invalid key (404), inactive chatbot (404), empty message (422), missing visitor_id (422), no auth required
- AI quality: personality response, knowledge base context, product suggestions

### 7e. Template tests (14 tests)

- `test_auth.py` (10): register, duplicate, short password, login, wrong password, nonexistent user, refresh, bad refresh, profile, unauthenticated
- `test_billing.py` (9): plans list, pricing, checkout, free plan fail, duplicate subscription, overview, overview after subscribe, current subscription, current after subscribe
- `test_api_keys.py` (5): create, list, revoke, auth via key, invalid key
- `test_health.py` (1): health check

---

## Step 8: Dashboard Pages

Three service-specific pages were added to the Next.js dashboard:

### 8a. Chatbots Page (`dashboard/src/app/chatbots/page.tsx`)

- Lists all chatbots with name, personality, widget key, active status
- Create chatbot form with name, personality, welcome message, theme config
- Edit / delete chatbot actions
- Widget key display for copy-paste embedding

### 8b. Knowledge Base Page (`dashboard/src/app/knowledge/page.tsx`)

- Lists all knowledge base entries across chatbots
- Filter by chatbot
- Create entry form with chatbot selector, source type dropdown, title, content, metadata
- Edit / delete entry actions
- Shows plan usage (e.g., "7 / 10 pages used")

### 8c. Conversations Page (`dashboard/src/app/conversations/page.tsx`)

- Lists conversations with chatbot name, visitor ID, status, message count, satisfaction score
- Filter by chatbot
- Detail view with full message history
- End conversation and rate conversation actions

### Dashboard Navigation (from `service.config.ts`)

| Label | Path | Icon |
|-------|------|------|
| Dashboard | `/` | LayoutDashboard |
| Chatbots | `/chatbots` | Bot |
| Knowledge Base | `/knowledge-base` | BookOpen |
| Conversations | `/conversations` | MessageSquare |
| Analytics | `/analytics` | BarChart3 |
| Widget | `/widget` | PanelBottomClose |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Step 9: Service Configuration

The dashboard branding and navigation were configured in `dashboard/src/service.config.ts`:

```typescript
export const serviceConfig: ServiceConfig = {
  name: "ShopChat",
  tagline: "AI Shopping Assistant",
  slug: "shopchat",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8108",
  colors: {
    primary: "oklch(0.55 0.20 275)",
    primaryHex: "#6366f1",
    accent: "oklch(0.70 0.18 290)",
    accentHex: "#818cf8",
  },
  fonts: {
    heading: "Outfit",
    body: "Inter",
  },
  navigation: [ /* 9 sidebar items */ ],
  plans: [
    { tier: "free", name: "Free", price: 0, features: [...] },
    { tier: "pro", name: "Pro", price: 19, features: [...] },
    { tier: "enterprise", name: "Enterprise", price: 79, features: [...] },
  ],
};
```

---

## Step 10: Landing Page

The landing page at `landing/` was configured with:
- Service name and tagline from the scaffold
- Feature highlights: AI chat, knowledge base, analytics, white-label
- Pricing table matching the plan tiers
- Call-to-action buttons linking to the dashboard registration page

---

## Implementation Summary

| Step | Component | Files Created/Modified |
|------|-----------|----------------------|
| 1 | Template Scaffolding | Entire service directory from template |
| 2 | Models | `chatbot.py`, `knowledge_base.py`, `conversation.py`, `message.py` |
| 3 | Services | `chatbot_service.py`, `knowledge_service.py`, `chat_service.py`, `analytics_service.py` |
| 4 | API Routes | `chatbots.py`, `knowledge.py`, `conversations.py`, `widget.py`, `analytics.py` |
| 5 | Plan Limits | `constants/plans.py` |
| 6 | Schemas | `schemas/chat.py` |
| 7 | Tests | `test_chatbots.py`, `test_knowledge.py`, `test_conversations.py`, `test_widget.py` |
| 8 | Dashboard Pages | `chatbots/page.tsx`, `knowledge/page.tsx`, `conversations/page.tsx` |
| 9 | Service Config | `service.config.ts` |
| 10 | Landing Page | `landing/` directory |
