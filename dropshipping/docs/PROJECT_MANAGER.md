# Project Manager Guide — Dropshipping Platform

## Overview

The dropshipping platform is the core product: multi-tenant store creation, product
management, order processing, fulfillment, and now integration with 8 AI-powered
SaaS services via the ServiceBridge.

---

## Feature Scope

### Core Platform (Phase 1)
- User registration and JWT authentication
- Multi-store management with settings
- Product CRUD with variants, images, inventory
- Order processing with Stripe checkout
- Supplier management and auto-fulfillment
- 30+ features including discounts, categories, reviews, analytics, themes, etc.

### ServiceBridge (Phase 3)
- Automatic event dispatch when products/orders/customers change
- HMAC-signed webhooks to 8 connected SaaS services
- Dashboard activity page with KPIs, filters, pagination
- Per-product and per-order service status panels
- Services hub with health indicators

---

## Milestones

| Milestone | Status | Tests |
|-----------|--------|-------|
| Core platform (30 features) | Complete | 541 |
| ServiceBridge backend | Complete | 39 |
| ServiceBridge dashboard UI | Complete | -- |
| ServiceBridge e2e tests | Complete | 15 |
| **Total** | **Complete** | **580 + 15 e2e** |

---

## Dependencies

- **8 SaaS services**: Each must have `POST /api/v1/webhooks/platform-events` receiver
- **Shared packages**: `ecomm_core` provides auth, billing, DB across all services
- **LLM Gateway**: Centralized AI provider routing (port 8200)
- **PostgreSQL**: Shared database with schema-based isolation per service

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend test count | 580 |
| API endpoints | 30+ |
| Celery task functions | 21 |
| ServiceBridge event types | 5 |
| Connected service slots | 8 |
| E2E test spec files | 25+ |
