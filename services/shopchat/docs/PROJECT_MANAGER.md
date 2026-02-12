# Project Manager Guide

**For Project Managers:** ShopChat (Feature A8) is an independently hostable SaaS product that provides an embeddable AI-powered chat widget for e-commerce stores. It can operate standalone or integrate with the dropshipping platform via API provisioning. This document covers the product overview, differentiators, architecture, current status, pricing, integration points, and risk register.

---

## Overview

ShopChat enables store owners to deploy an AI shopping assistant on their website in minutes. The assistant answers customer questions using a configurable knowledge base, recommends products from the catalog, and provides 24/7 automated support. Store owners manage their chatbots, knowledge base, conversations, and analytics through a branded dashboard.

---

## Key Differentiators

| Differentiator | Description |
|---------------|-------------|
| **Embeddable Widget** | Vanilla JS snippet -- no React or framework dependency. Store owners paste a single `<script>` tag. Visitors chat immediately without login. |
| **AI-Powered Responses** | Claude API integration provides intelligent, context-aware answers. The chatbot understands product catalogs, policies, and custom Q&A. |
| **Knowledge Base (RAG)** | Store owners build a knowledge base from product catalogs, policy pages, FAQs, custom text, and URLs. The AI searches this knowledge base for every visitor query to provide accurate, store-specific answers. |
| **White-Label Option** | Enterprise tier removes ShopChat branding. The widget becomes a fully white-labeled part of the store experience. |
| **Conversation Analytics** | Dashboard analytics show conversation volume, average satisfaction scores, top chatbots, and per-chatbot performance breakdowns. |
| **Multi-Chatbot Support** | Each account can create multiple chatbots with distinct personalities, welcome messages, and visual themes. |

---

## Architecture

ShopChat follows the standard microservice template used across the platform:

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | 8108 |
| Dashboard | Next.js 16 (App Router) + Tailwind | 3108 |
| Landing Page | Next.js 16 (static) | 3208 |
| Database | PostgreSQL 16 | 5508 |
| Cache / Queue | Redis 7 | 6408 |
| Task Queue | Celery | -- |

### Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts with email, plan tier, Stripe customer ID |
| `subscriptions` | Stripe subscription tracking |
| `api_keys` | Programmatic API key access for integrations |
| `chatbots` | Chatbot instances with personality, theme config, widget key |
| `knowledge_base` | Knowledge entries (product catalog, policies, FAQs, custom Q&A) |
| `conversations` | Chat sessions with visitor tracking and satisfaction rating |
| `messages` | Individual messages (user/assistant roles) within conversations |

---

## Current Status

| Metric | Value |
|--------|-------|
| Backend tests | **88** (highest tied with FlowSend) |
| Dashboard pages | **9** (home, chatbots, knowledge, conversations, billing, API keys, settings, login, register) |
| API endpoints | **25+** across auth, chatbots, knowledge, conversations, widget, analytics, billing, API keys, usage, health |
| Database models | **7** (User, Subscription, ApiKey, Chatbot, KnowledgeBase, Conversation, Message) |
| Plan tiers | **3** (Free, Pro, Enterprise) |

### Feature Completeness

| Feature | Status | Notes |
|---------|--------|-------|
| Chatbot CRUD | Complete | Create, list, get, update, delete with user scoping |
| Knowledge Base CRUD | Complete | Full CRUD with plan limit enforcement and source type support |
| Widget Configuration | Complete | Public endpoint returns chatbot config by widget_key |
| Widget Chat | Complete | Public endpoint for visitor chat with AI responses |
| Conversation Management | Complete | List, detail with messages, end, rate with satisfaction score |
| Analytics | Complete | Overview and per-chatbot analytics |
| Billing / Subscriptions | Complete | Stripe integration with checkout, portal, billing overview |
| API Key Management | Complete | Create, list, revoke, auth via X-API-Key header |
| User Provisioning | Complete | Cross-service user creation via API |
| AI Response Generation | Mock | Uses keyword matching and personality prefixes; production needs Claude API |

---

## Pricing

| Tier | Price/mo | Conversations/mo | Knowledge Base | Customization | Analytics | API Access | Trial |
|------|----------|-----------------|----------------|---------------|-----------|------------|-------|
| **Free** | $0 | 50 | Basic (10 pages) | Branding only | Basic | No | -- |
| **Pro** | $19 | 1,000 | Full catalog (500 pages) | Personality + flows | Full | Yes | 14 days |
| **Enterprise** | $79 | Unlimited | Unlimited + API | White-label | Full + export + webhooks | Yes | 14 days |

### Billing Metrics

The two primary billing metrics are:
1. **Conversations per month** (`max_items`) -- counted across all chatbots for a user. Widget chat returns 429 when the limit is reached.
2. **Knowledge base pages** (`max_secondary`) -- counted across all chatbots for a user. API returns 403 when the limit is reached.

---

## Integration with Dropshipping Platform

ShopChat integrates with the main dropshipping platform through:

1. **User Provisioning**: The platform calls `POST /api/v1/auth/provision` with admin API key credentials to create a ShopChat user account linked to the platform user. Returns a service-specific API key.

2. **Usage Reporting**: The platform polls `GET /api/v1/usage` (authenticated via API key) to retrieve billing metrics (conversations used, knowledge pages used, plan tier) for display on the platform's unified billing dashboard.

3. **Stripe Webhooks**: Subscription changes flow through Stripe webhooks to update the user's plan tier. The platform does not directly manage subscriptions -- it delegates to ShopChat's Stripe integration.

4. **Cross-Service Identity**: Each ShopChat user optionally stores `external_platform_id` and `external_store_id` for linking back to the dropshipping platform.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **AI response quality** | Medium | High | Currently using mock responses. Production deployment requires Claude API integration with proper prompt engineering, guardrails, and content safety filters. |
| **Widget abuse** | Medium | Medium | Public widget endpoints have no rate limiting in current implementation. Production needs rate limiting per widget_key and per visitor_id. |
| **Knowledge base scaling** | Low | Medium | Current keyword search is O(n) per query. For large knowledge bases (1000+ entries), implement vector embeddings and semantic search. |
| **Stripe integration** | Low | High | Currently uses mock mode for testing. Stripe Price IDs must be configured via environment variables before production launch. |
| **Multi-tenant data leakage** | Low | Critical | All queries are scoped by user_id through chatbot ownership. Cross-user access returns 404. Thoroughly tested in 88 backend tests. |
| **Conversation limit bypass** | Low | Medium | Limits are checked server-side before conversation creation. The widget chat endpoint looks up the chatbot owner to enforce their plan limits. |

---

## Milestones / Next Steps

1. **Claude API Integration**: Replace mock `_generate_ai_response()` with real Claude API calls for production-quality responses.
2. **Vector Embeddings**: Add embedding storage to knowledge base entries for semantic search (current implementation uses keyword matching).
3. **Rate Limiting**: Apply per-widget-key and per-visitor-id rate limits to public widget endpoints.
4. **Widget Customization UI**: Dashboard page for configuring widget appearance (position, size, colors, branding).
5. **Analytics Export**: CSV/PDF export of conversation analytics for Enterprise tier.
6. **Webhook Notifications**: Send webhook events for new conversations, satisfaction ratings, and conversation endings.
