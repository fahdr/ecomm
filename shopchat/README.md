# ShopChat

> AI Shopping Assistant

## Overview

ShopChat is an independently hostable SaaS product that provides an embeddable AI-powered
chat widget for e-commerce stores. It uses Claude AI with a knowledge base built from
product catalogs, policy pages, and custom Q&A to answer customer questions, recommend
products, and provide support. Can be used standalone or integrated with the dropshipping
platform.

**For Developers:**
    Feature logic in `chatbot_service.py` (chatbot config + widget key generation),
    `knowledge_service.py` (knowledge base CRUD + embedding), and
    `conversation_service.py` (message history + AI responses). Dashboard is
    config-driven via `dashboard/src/service.config.ts`.

**For Project Managers:**
    ShopChat is Feature A8. Has the highest test count tied with FlowSend at 88
    backend tests and 3 dashboard feature pages. Pricing: Free ($0), Pro ($19/mo),
    Enterprise ($79/mo).

**For QA Engineers:**
    Test chatbot CRUD, knowledge base entry lifecycle, conversation flow (create →
    messages → end → rate), widget key generation, satisfaction scoring, and plan
    limit enforcement on conversations and knowledge entries.

**For End Users:**
    Add an intelligent chat assistant to your store in minutes. Build a knowledge base
    from your product catalog, customize the chatbot personality, and let AI handle
    customer questions 24/7 while you focus on growing your business.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8108 |
| Dashboard | Next.js 16 + Tailwind | 3108 |
| Landing Page | Next.js 16 (static) | 3208 |
| Database | PostgreSQL 16 | 5508 |
| Cache/Queue | Redis 7 | 6408 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8108 | **Docs**: http://localhost:8108/docs
- **Dashboard**: http://localhost:3108
- **Landing Page**: http://localhost:3208

## Core Features

### Chatbot Management
- Create multiple chatbots with distinct personalities and welcome messages
- Custom theme configuration to match store branding
- Auto-generated widget key for embed snippet
- Active/inactive toggle

### Knowledge Base
- Source types: product catalog, policy pages, custom text, URL import
- Content storage with optional embedding vectors for semantic search
- Per-chatbot knowledge scope
- Plan-enforced limits (Free: 10 pages, Pro: full catalog, Enterprise: unlimited)

### Conversations
- Real-time message history (user + assistant roles)
- Conversation lifecycle: active → ended
- Satisfaction rating per conversation (1-5 scale)
- Claude AI powered responses with knowledge base context

### Embeddable Widget
- Vanilla JS snippet (no framework dependency)
- Configurable theming (match store colors)
- White-label option (Enterprise tier)

## API Endpoints

### Chatbots
```
POST   /api/v1/chatbots                  — Create chatbot (generates widget_key)
GET    /api/v1/chatbots                  — List chatbots with pagination
GET    /api/v1/chatbots/{chatbot_id}     — Chatbot details
PATCH  /api/v1/chatbots/{chatbot_id}     — Update chatbot config
DELETE /api/v1/chatbots/{chatbot_id}     — Delete chatbot + all data
```

### Knowledge Base
```
POST   /api/v1/knowledge                 — Create knowledge entry (enforces plan limits)
GET    /api/v1/knowledge                 — List entries with optional chatbot filter
GET    /api/v1/knowledge/{entry_id}      — Entry details
PATCH  /api/v1/knowledge/{entry_id}      — Update entry
DELETE /api/v1/knowledge/{entry_id}      — Delete entry
```

### Conversations
```
GET  /api/v1/conversations                          — List conversations (optional chatbot filter)
GET  /api/v1/conversations/{conversation_id}        — Conversation with full message history
POST /api/v1/conversations/{conversation_id}/end    — End active conversation
POST /api/v1/conversations/{conversation_id}/rate   — Rate with satisfaction score (1-5)
```

## Pricing

| Tier | Price/mo | Conversations/mo | Knowledge Base | Customization | Analytics |
|------|----------|-----------------|----------------|---------------|-----------|
| Free | $0 | 50 | Basic (10 pages) | Branding only | Basic |
| Pro | $19 | 1,000 | Full catalog sync | Personality + flows | Full |
| Enterprise | $79 | Unlimited | Unlimited + API | White-label | Full + export + webhooks |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `chatbots` | Chatbot instances with personality, theme, widget key |
| `knowledge_bases` | Knowledge entries (product catalog, policies, custom Q&A) |
| `conversations` | Chat sessions with visitor tracking and satisfaction rating |
| `messages` | Individual messages (user/assistant) within conversations |

## Testing

```bash
make test-backend    # 88 backend unit tests
```

## Design System

- **Primary**: Indigo — `oklch(0.55 0.20 275)` / `#6366f1`
- **Accent**: Light Indigo — `oklch(0.70 0.18 290)` / `#818cf8`
- **Heading font**: Outfit (conversational, friendly)
- **Body font**: Inter

## License

Proprietary — All rights reserved.
