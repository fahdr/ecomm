# ShopChat Documentation

> AI Shopping Assistant for E-Commerce Stores

ShopChat is an embeddable AI-powered chat widget that provides 24/7 customer support, product recommendations, and intelligent answers based on a customizable knowledge base. Store owners manage chatbots, conversations, and analytics through a dedicated dashboard.

---

## Quick Links

| Document | Audience | Purpose |
|----------|----------|---------|
| [Setup Guide](SETUP.md) | Developers | Local development, environment configuration, services |
| [Architecture](ARCHITECTURE.md) | Developers, Tech Leads | System design, data models, technical decisions |
| [API Reference](API_REFERENCE.md) | Developers, QA | Endpoint documentation, request/response formats |
| [Testing Guide](TESTING.md) | Developers, QA | Test infrastructure, running tests, writing tests |
| [QA Engineer Guide](QA_ENGINEER.md) | QA Engineers | Acceptance criteria, verification checklists, edge cases |
| [Project Manager Guide](PROJECT_MANAGER.md) | Project Managers | Product overview, milestones, risk register |
| [End User Guide](END_USER.md) | Merchants | Feature walkthroughs, getting started, tips |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | All | Build history, development chronology |

---

## Service Overview

**Name:** ShopChat
**Tagline:** AI Shopping Assistant
**Ports:** Backend 8108 · Dashboard 3108 · Landing 3208
**Database:** PostgreSQL 16 (port 5508) · Redis 7 (port 6408)

### Key Features

- **Embeddable Widget**: Vanilla JS snippet, no framework dependency
- **AI-Powered Responses**: Claude API integration with RAG knowledge base
- **Multi-Chatbot Support**: Create multiple chatbots with distinct personalities
- **Knowledge Base**: Product catalogs, policies, FAQs, custom Q&A
- **Conversation Tracking**: Full message history with satisfaction ratings
- **Analytics Dashboard**: Conversation volume, satisfaction scores, chatbot performance
- **White-Label Option**: Enterprise tier removes ShopChat branding
- **Plan Enforcement**: Free (50 conversations/mo), Pro (1,000), Enterprise (unlimited)

---

## Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | **113** |
| Dashboard Pages | **9** (home, chatbots, knowledge, conversations, billing, API keys, settings, login, register) |
| API Endpoints | **25+** (auth, chatbots, knowledge, conversations, widget, analytics, billing, API keys, usage, health) |
| Database Models | **7** (User, Subscription, ApiKey, Chatbot, KnowledgeBase, Conversation, Message) |
| Plan Tiers | **3** (Free, Pro, Enterprise) |

### Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_knowledge.py` | 26 | Knowledge base CRUD, plan limits, ownership, source types |
| `test_chatbots.py` | 21 | Chatbot CRUD, widget key uniqueness, user scoping |
| `test_conversations.py` | 17 | List, detail, end, rate conversations |
| `test_widget.py` | 16 | Public config, chat flow, AI responses, product suggestions |
| `test_auth.py` | 10 | Register, login, refresh, profile |
| `test_billing.py` | 9 | Plans, checkout, portal, billing overview |
| `test_api_keys.py` | 5 | Create, list, revoke, auth via API key |
| `test_health.py` | 1 | Health check endpoint |
| **Total** | **113** | |

---

## Getting Started

```bash
# Install dependencies, run migrations, start all services
make install && make migrate && make start
```

**Access Points:**
- API: http://localhost:8108
- API Docs: http://localhost:8108/docs
- Dashboard: http://localhost:3108
- Landing Page: http://localhost:3208

---

## Design System

| Element | Value |
|---------|-------|
| Primary Color | Indigo – `oklch(0.55 0.20 275)` / `#6366f1` |
| Accent Color | Light Indigo – `oklch(0.70 0.18 290)` / `#818cf8` |
| Heading Font | Outfit (conversational, friendly) |
| Body Font | Lexend |

---

## Pricing Tiers

| Tier | Price/mo | Conversations/mo | Knowledge Pages | API Access |
|------|----------|-----------------|----------------|------------|
| Free | $0 | 50 | 10 | No |
| Pro | $19 | 1,000 | 500 | Yes |
| Enterprise | $79 | Unlimited | Unlimited | Yes |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
