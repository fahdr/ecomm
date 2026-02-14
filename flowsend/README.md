# FlowSend

> Smart Email Marketing

## Overview

FlowSend is an independently hostable SaaS product for email marketing automation.
It provides contact management, visual email flow builders, broadcast campaigns,
template editing, A/B testing, and delivery analytics. Can be used standalone or
integrated with the dropshipping platform.

**For Developers:**
    FlowSend has the most complex data model (10+ tables). Feature logic in
    `contact_service.py`, `flow_service.py`, `campaign_service.py`, `template_service.py`,
    and `analytics_service.py`. Flow execution runs via Celery tasks with step-by-step
    processing. Dashboard is config-driven via `dashboard/src/service.config.ts`.

**For Project Managers:**
    FlowSend is Feature A4. Has the highest test count at 87 backend tests and 3
    dashboard feature pages. Pricing: Free ($0), Pro ($39/mo), Enterprise ($149/mo).

**For QA Engineers:**
    Test contact import + list management, flow lifecycle (draft → active → paused),
    campaign send + event tracking, template CRUD, analytics aggregation, and plan
    limit enforcement. CAN-SPAM compliance in unsubscribe handling.

**For End Users:**
    Automate your email marketing with visual flow builders. Create abandoned cart
    sequences, welcome series, and win-back campaigns. Track opens, clicks, and
    conversions with detailed analytics.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8104 |
| Dashboard | Next.js 16 + Tailwind | 3104 |
| Landing Page | Next.js 16 (static) | 3204 |
| Database | PostgreSQL 16 | 5504 |
| Cache/Queue | Redis 7 | 6404 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8104 | **Docs**: http://localhost:8104/docs
- **Dashboard**: http://localhost:3104
- **Landing Page**: http://localhost:3204

## Core Features

### Contact Management
- Import contacts via CSV or bulk email list
- Tag-based segmentation and custom fields
- Static and dynamic contact lists with rule-based membership
- Subscription status tracking (CAN-SPAM compliant unsubscribe)

### Visual Flow Builder
- Create automated email sequences: trigger → delay → send → condition → branch
- Flow triggers: abandoned cart, post-purchase, welcome, win-back, custom events
- Step-by-step execution tracking via Celery
- Flow lifecycle: draft → active → paused

### Broadcast Campaigns
- One-time email sends to contact lists or segments
- Campaign scheduling for future delivery
- Per-campaign analytics: sent, delivered, opened, clicked, bounced
- A/B testing for subject lines (Pro+)

### Email Templates
- System templates (pre-built) + custom user templates
- HTML content with text fallback
- Template preview and thumbnail generation

### Analytics
- Aggregate metrics: delivery rate, open rate, click rate, bounce rate
- Per-campaign breakdown with event timeline
- Contact engagement scoring

## API Endpoints

### Contacts
```
POST   /api/v1/contacts                  — Create contact (enforces plan limits)
GET    /api/v1/contacts                  — List with search/tag filter + pagination
GET    /api/v1/contacts/count            — Total contact count
GET    /api/v1/contacts/{contact_id}     — Contact details
PATCH  /api/v1/contacts/{contact_id}     — Update contact
DELETE /api/v1/contacts/{contact_id}     — Delete contact
POST   /api/v1/contacts/import           — Bulk import emails/CSV
POST   /api/v1/contacts/lists            — Create contact list
GET    /api/v1/contacts/lists            — List contact lists
DELETE /api/v1/contacts/lists/{list_id}  — Delete list
```

### Flows
```
POST   /api/v1/flows                     — Create flow (draft status)
GET    /api/v1/flows                     — List with status filter
GET    /api/v1/flows/{flow_id}           — Flow details
PATCH  /api/v1/flows/{flow_id}           — Update flow (draft/paused only)
DELETE /api/v1/flows/{flow_id}           — Delete flow
POST   /api/v1/flows/{flow_id}/activate  — Activate flow (requires steps)
POST   /api/v1/flows/{flow_id}/pause     — Pause active flow
GET    /api/v1/flows/{flow_id}/executions — List flow executions
```

### Campaigns
```
POST   /api/v1/campaigns                        — Create campaign
GET    /api/v1/campaigns                        — List with status filter
GET    /api/v1/campaigns/{campaign_id}          — Campaign details
PATCH  /api/v1/campaigns/{campaign_id}          — Update (draft/scheduled only)
DELETE /api/v1/campaigns/{campaign_id}          — Delete campaign
POST   /api/v1/campaigns/{campaign_id}/send     — Send campaign
GET    /api/v1/campaigns/{campaign_id}/analytics — Campaign analytics
GET    /api/v1/campaigns/{campaign_id}/events    — Event list
```

### Templates
```
POST   /api/v1/templates                 — Create email template
GET    /api/v1/templates                 — List system + custom templates
GET    /api/v1/templates/{template_id}   — Template details
PATCH  /api/v1/templates/{template_id}   — Update custom template
DELETE /api/v1/templates/{template_id}   — Delete custom template
```

### Analytics
```
GET /api/v1/analytics                    — Aggregate analytics (totals, rates, per-campaign)
```

## Pricing

| Tier | Price/mo | Emails/mo | Flows | Contacts | A/B Testing |
|------|----------|----------|-------|----------|-------------|
| Free | $0 | 500 | 2 | 250 | No |
| Pro | $39 | 25,000 | 20 | 10,000 | Yes |
| Enterprise | $149 | Unlimited | Unlimited | Unlimited | Yes + API + Dedicated IP |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `contacts` | Email contacts with tags and custom fields |
| `contact_lists` | Static/dynamic contact lists |
| `email_templates` | System + user email templates |
| `flows` | Automated email sequences with trigger config |
| `flow_executions` | Per-contact flow execution tracking |
| `campaigns` | Broadcast email campaigns |
| `email_events` | Delivery tracking (sent, opened, clicked, bounced) |
| `unsubscribes` | CAN-SPAM compliant unsubscribe records |

## Testing

```bash
make test-backend    # 87 backend unit tests
```

## Design System

- **Primary**: Coral Red — `oklch(0.65 0.20 25)` / `#f43f5e`
- **Accent**: Orange — `oklch(0.75 0.18 40)` / `#fb923c`
- **Heading font**: Satoshi (friendly, approachable)
- **Body font**: Inter

## License

Proprietary — All rights reserved.
