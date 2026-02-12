# QA Engineer Guide

**For QA Engineers:** This guide covers everything needed to test the ShopChat AI Shopping Assistant service. It includes the test stack, how to run the 88 backend tests, coverage breakdown, API endpoint reference, and verification checklists for every feature area.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and framework |
| pytest-asyncio | Async test support for FastAPI |
| httpx | Async HTTP test client |
| SQLAlchemy + asyncpg | Test database operations |
| PostgreSQL 16 | Test database (same as production, truncated between tests) |

---

## Running Tests

### Full Test Suite (88 tests)

```bash
# From the service root
make test-backend

# From the backend directory with verbose output
cd backend && pytest -v

# With specific markers
cd backend && pytest -v -x    # stop on first failure
cd backend && pytest -v -k "chatbot"  # run only chatbot tests
```

### Individual Test Files

```bash
cd backend && pytest tests/test_chatbots.py -v        # 21 tests
cd backend && pytest tests/test_knowledge.py -v        # 26 tests
cd backend && pytest tests/test_conversations.py -v    # 17 tests
cd backend && pytest tests/test_widget.py -v           # 16 tests
cd backend && pytest tests/test_auth.py -v             # 10 tests
cd backend && pytest tests/test_billing.py -v          #  9 tests
cd backend && pytest tests/test_api_keys.py -v         #  5 tests
cd backend && pytest tests/test_health.py -v           #  1 test
```

### Single Test

```bash
cd backend && pytest tests/test_widget.py::test_widget_chat_with_knowledge_base -v
```

---

## Coverage Table

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_knowledge.py` | 26 | Knowledge base CRUD, plan limits, ownership, source types, pagination, scoping |
| `test_chatbots.py` | 21 | Chatbot CRUD, widget key uniqueness, user scoping, theme config, validation |
| `test_conversations.py` | 17 | List, detail (with messages), end, rate (1-5 range), pagination, scoping |
| `test_widget.py` | 16 | Public config, chat flow, AI responses, knowledge base context, product suggestions |
| `test_auth.py` | 10 | Register, login, refresh, profile, duplicate email, invalid credentials |
| `test_billing.py` | 9 | Plan listing, checkout, duplicate subscription, billing overview, current subscription |
| `test_api_keys.py` | 5 | Create, list, revoke, auth via X-API-Key, invalid key |
| `test_health.py` | 1 | Health check endpoint returns 200 with service metadata |
| **Total** | **88** | |

---

## Test Structure

### Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single asyncio event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before each test, truncates all tables with CASCADE after. Terminates non-self DB connections to prevent deadlocks. |
| `db` | function | Raw async database session for direct model operations |
| `client` | function | `httpx.AsyncClient` bound to the FastAPI app at `http://test` |
| `auth_headers` | function | Registers a fresh user and returns `{"Authorization": "Bearer <token>"}` |

### Helper Functions

| Helper | Location | Purpose |
|--------|----------|---------|
| `register_and_login(client, email)` | `conftest.py` | Registers a user and returns auth headers. Generates random email if not provided. |
| `create_test_chatbot(client, headers, name)` | `test_chatbots.py` | Creates a chatbot via the API and returns the JSON response. |
| `create_test_entry(client, headers, chatbot_id, ...)` | `test_knowledge.py` | Creates a knowledge base entry via the API. |
| `send_widget_message(client, widget_key, visitor_id, message)` | `test_conversations.py` | Sends a chat message through the public widget endpoint. |
| `create_chatbot_and_conversation(client, headers, ...)` | `test_conversations.py` | Creates a chatbot and starts a conversation in one step. |
| `create_authenticated_chatbot(client, ...)` | `test_widget.py` | Registers a user, creates a chatbot, and returns both auth headers and chatbot data. |

---

## API Documentation

Interactive API docs are available at **http://localhost:8108/docs** (Swagger UI) when the backend is running.

---

## Endpoint Summary

### Auth (`/api/v1/auth/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| POST | `/auth/register` | None | 201 | Register new user, returns JWT tokens |
| POST | `/auth/login` | None | 200 | Login with email + password, returns JWT tokens |
| POST | `/auth/refresh` | None | 200 | Refresh expired access token using refresh token |
| GET | `/auth/me` | JWT | 200 | Get authenticated user profile |
| POST | `/auth/forgot-password` | None | 200 | Request password reset (stub) |
| POST | `/auth/provision` | API Key | 201 | Provision user from dropshipping platform |

### Chatbots (`/api/v1/chatbots/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| POST | `/chatbots` | JWT | 201 | Create chatbot (generates widget_key) |
| GET | `/chatbots` | JWT | 200 | List chatbots with pagination |
| GET | `/chatbots/{chatbot_id}` | JWT | 200 | Get chatbot details |
| PATCH | `/chatbots/{chatbot_id}` | JWT | 200 | Update chatbot (name, personality, theme, active) |
| DELETE | `/chatbots/{chatbot_id}` | JWT | 204 | Delete chatbot + all related data |

### Knowledge Base (`/api/v1/knowledge/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| POST | `/knowledge` | JWT | 201 | Create knowledge entry (enforces plan limits) |
| GET | `/knowledge` | JWT | 200 | List entries (optional `chatbot_id` filter) |
| GET | `/knowledge/{entry_id}` | JWT | 200 | Get single entry |
| PATCH | `/knowledge/{entry_id}` | JWT | 200 | Update entry fields |
| DELETE | `/knowledge/{entry_id}` | JWT | 204 | Delete entry |

### Conversations (`/api/v1/conversations/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/conversations` | JWT | 200 | List conversations (optional `chatbot_id` filter) |
| GET | `/conversations/{conversation_id}` | JWT | 200 | Conversation detail with full message history |
| POST | `/conversations/{conversation_id}/end` | JWT | 200 | End an active conversation |
| POST | `/conversations/{conversation_id}/rate` | JWT | 200 | Rate conversation (score: 1.0-5.0) |

### Messages (embedded in Conversations)

Messages are returned as part of the conversation detail response. Each message has:
- `id`: UUID
- `role`: `"user"` or `"assistant"`
- `content`: Message text
- `metadata`: Optional JSON (product suggestions, links)
- `created_at`: Timestamp

### Widget (`/api/v1/widget/`) -- PUBLIC, no auth required

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/widget/config/{widget_key}` | None | 200 | Get widget configuration for rendering |
| POST | `/widget/chat` | None | 200 | Send message, get AI response + product suggestions |

**Widget chat request body:**
```json
{
  "widget_key": "wk_...",
  "visitor_id": "session-based-id",
  "message": "Do you have running shoes?",
  "visitor_name": "Alice"       // optional
}
```

**Widget chat response:**
```json
{
  "conversation_id": "uuid",
  "message": "AI response text",
  "product_suggestions": [
    { "name": "Blue Running Shoes", "price": "$89.99", "url": "/products/blue-shoes" }
  ]
}
```

### Analytics (`/api/v1/analytics/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/analytics/overview` | JWT | 200 | Aggregated metrics (total conversations, messages, avg satisfaction, active chatbots, today's count) |
| GET | `/analytics/chatbots` | JWT | 200 | Per-chatbot breakdown (conversations, messages, avg satisfaction, avg messages/conversation) |

### Billing (`/api/v1/billing/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/billing/plans` | None | 200 | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe checkout session |
| POST | `/billing/portal` | JWT | 200 | Create Stripe customer portal session |
| GET | `/billing/current` | JWT | 200 | Get current subscription (null if none) |
| GET | `/billing/overview` | JWT | 200 | Full billing overview (plan, subscription, usage) |

### API Keys (`/api/v1/api-keys/`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| POST | `/api-keys` | JWT | 201 | Create API key (returns raw key once) |
| GET | `/api-keys` | JWT | 200 | List API keys (prefix only, no raw key) |
| DELETE | `/api-keys/{key_id}` | JWT | 204 | Revoke an API key |

### Usage (`/api/v1/usage`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/usage` | JWT or API Key | 200 | Usage metrics for billing period |

### Health (`/api/v1/health`)

| Method | Endpoint | Auth | Status | Description |
|--------|----------|------|--------|-------------|
| GET | `/health` | None | 200 | Service health check |

---

## Verification Checklist

### Authentication

- [ ] Register with valid email + password (201, returns tokens)
- [ ] Register with duplicate email returns 409
- [ ] Register with short password (<8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with nonexistent email returns 401
- [ ] Refresh with valid refresh token returns new token pair
- [ ] Refresh with access token (wrong type) returns 401
- [ ] GET /auth/me with valid token returns user profile
- [ ] GET /auth/me without token returns 401

### Chatbot CRUD

- [ ] Create chatbot returns 201 with `widget_key`, `id`, `created_at`
- [ ] Create chatbot with custom personality and welcome_message
- [ ] Create chatbot with custom theme_config stores correctly
- [ ] Create chatbot without auth returns 401
- [ ] Create chatbot with empty name returns 422
- [ ] List chatbots returns paginated response (items, total, page, page_size)
- [ ] List chatbots with pagination parameters works correctly
- [ ] List chatbots only shows current user's chatbots (user scoping)
- [ ] Get chatbot by ID returns correct details
- [ ] Get nonexistent chatbot returns 404
- [ ] Get another user's chatbot returns 404 (not 403)
- [ ] Update chatbot name preserves other fields
- [ ] Update chatbot personality, welcome_message, theme_config, is_active
- [ ] Update nonexistent chatbot returns 404
- [ ] Delete chatbot returns 204 and removes it from list
- [ ] Delete another user's chatbot returns 404
- [ ] Each chatbot has a unique widget_key

### Knowledge Base

- [ ] Create entry with chatbot_id, title, content, source_type returns 201
- [ ] Create entry with metadata stores correctly
- [ ] Create entry for nonexistent chatbot returns 404
- [ ] Create entry for another user's chatbot returns 404
- [ ] Create entry without auth returns 401
- [ ] Create entry with empty title or content returns 422
- [ ] List entries returns all entries across user's chatbots
- [ ] List entries with `chatbot_id` filter returns only that chatbot's entries
- [ ] List entries with pagination works correctly
- [ ] List entries with nonexistent chatbot_id returns 404
- [ ] List entries does not return other users' entries
- [ ] Get single entry by ID returns correct data
- [ ] Get nonexistent entry returns 404
- [ ] Get another user's entry returns 404
- [ ] Update entry title, content, source_type, metadata, is_active
- [ ] Update nonexistent entry returns 404
- [ ] Update another user's entry returns 404
- [ ] Delete entry returns 204, reduces list count
- [ ] Delete another user's entry returns 404
- [ ] All source types accepted: `product_catalog`, `policy_page`, `faq`, `custom_text`, `url`

### Conversations

- [ ] List conversations returns paginated response
- [ ] List conversations with chatbot_id filter
- [ ] List conversations with pagination
- [ ] List conversations does not show other users' conversations
- [ ] Get conversation detail includes messages array
- [ ] Messages include user message and assistant response (at least 2)
- [ ] Get nonexistent conversation returns 404
- [ ] Get another user's conversation returns 404
- [ ] End active conversation sets status to "ended" and ended_at
- [ ] End already-ended conversation returns 400
- [ ] End nonexistent conversation returns 404
- [ ] Rate conversation with score 1.0-5.0 stores correctly
- [ ] Rate with score < 1.0 returns 422
- [ ] Rate with score > 5.0 returns 422
- [ ] Rate nonexistent conversation returns 404
- [ ] Rate another user's conversation returns 404
- [ ] Message count increments with each message pair

### Widget (Public API -- no auth)

- [ ] GET `/widget/config/{widget_key}` returns chatbot config without auth
- [ ] Config includes chatbot_name, personality, welcome_message, theme_config, is_active
- [ ] Config with custom theme returns correct theme values
- [ ] Config with invalid widget_key returns 404
- [ ] Config with inactive chatbot returns 404
- [ ] POST `/widget/chat` sends message and receives AI response without auth
- [ ] Chat response includes conversation_id, message, product_suggestions
- [ ] Chat creates new conversation on first message from a visitor
- [ ] Chat continues same conversation for same visitor_id
- [ ] Chat creates separate conversations for different visitor_ids
- [ ] Chat stores visitor_name if provided
- [ ] Chat with invalid widget_key returns 404
- [ ] Chat with inactive chatbot returns 404
- [ ] Chat with empty message returns 422
- [ ] Chat with missing visitor_id returns 422
- [ ] Chat uses knowledge base entries for contextual responses
- [ ] Chat returns product suggestions from catalog entries

### Analytics

- [ ] Overview returns total_conversations, total_messages, avg_satisfaction, active_chatbots, conversations_today
- [ ] Per-chatbot analytics returns breakdown for each chatbot
- [ ] Analytics handles zero data (new account) gracefully
- [ ] Analytics handles null satisfaction scores correctly

### Billing

- [ ] List plans returns 3 tiers (free, pro, enterprise) with pricing
- [ ] Checkout for pro plan returns checkout_url and session_id
- [ ] Checkout for free plan returns 400
- [ ] Duplicate subscription checkout returns 400
- [ ] Billing overview shows current plan, subscription status, and usage
- [ ] Current subscription returns null when no subscription
- [ ] Current subscription returns subscription data after checkout

### API Keys

- [ ] Create API key returns raw key (shown only once)
- [ ] List API keys returns key_prefix but NOT the raw key
- [ ] Revoke API key sets is_active to false
- [ ] Auth via X-API-Key header works for usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification

### Plan Limit Enforcement

| Resource | Free | Pro | Enterprise |
|----------|------|-----|-----------|
| Conversations/month | 50 | 1,000 | Unlimited |
| Knowledge base pages | 10 | 500 | Unlimited |
| Trial days | 0 | 14 | 14 |
| API access | No | Yes | Yes |

- [ ] Free user creating 11th knowledge entry gets 403
- [ ] Pro user creating 501st knowledge entry gets 403
- [ ] Enterprise user can create unlimited entries
- [ ] Free user with 51st conversation gets 429 on widget chat
- [ ] Enterprise user can have unlimited conversations

### Cross-User Security

Every endpoint that retrieves, updates, or deletes a resource must return 404 (not 403) when a different user's resource is accessed. This prevents information leakage about resource existence.

- [ ] Chatbot: GET, PATCH, DELETE of another user's chatbot returns 404
- [ ] Knowledge: GET, PATCH, DELETE of another user's entry returns 404
- [ ] Conversation: GET, end, rate of another user's conversation returns 404
