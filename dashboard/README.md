# Dashboard

> Dropshipping Platform Admin Dashboard

## Overview

The dashboard is the primary admin interface for the dropshipping platform. Store owners
use it to manage products, orders, customers, themes, analytics, billing, and AI/automation
services. Built with Next.js 16 (App Router), Tailwind CSS, and shadcn/ui components.

**For Developers:**
    The dashboard uses a shell layout with collapsible sidebar (platform mode + store mode).
    Pages are under `src/app/`, components under `src/components/`, API client at `src/lib/api.ts`.
    Design system uses OKLCH colors (teal primary, amber accent) with Bricolage Grotesque +
    Instrument Sans + IBM Plex Mono fonts. Motion animations via CSS + custom primitives.

**For Project Managers:**
    36 pages total covering stores, products, orders, fulfillment, customers, discounts,
    categories, suppliers, reviews, analytics, billing, themes, teams, notifications,
    domains, currency, search, A/B tests, fraud, bulk ops, gift cards, segments, upsells,
    exports, and AI services integration. All pages build cleanly.

**For QA Engineers:**
    E2E tests in `/e2e/tests/dashboard/` cover all critical flows. Key patterns: paginated
    response unwrapping, Decimal string formatting, sidebar navigation, and theme switching.
    190+ tests across 25 spec files.

**For End Users:**
    Your central hub for managing your dropshipping business. Create stores, add products,
    process orders, track analytics, customize themes, and connect AI automation tools.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Dashboard | Next.js 16 (App Router) | 3000 |
| Backend API | FastAPI | 8000 |
| Database | PostgreSQL 16 | 5432 |

## Quick Start

```bash
cd dashboard
npm install
npm run dev    # → http://localhost:3000
```

## Design System

- **Colors**: OKLCH (teal primary `oklch(0.72 0.12 192)`, amber accent `oklch(0.80 0.15 85)`)
- **Fonts**: Bricolage Grotesque (headings), Instrument Sans (body), IBM Plex Mono (code)
- **Components**: shadcn/ui (Button, Card, Badge, Dialog, Input, Select, Table, Skeleton, etc.)
- **Motion**: FadeIn, StaggerChildren, SlideIn, ScaleIn, ScrollReveal primitives
- **Layout**: Top bar + collapsible sidebar (platform/store mode) + shell wrapper

## Page Structure

### Platform Mode (top-level)
| Page | Path | Description |
|------|------|-------------|
| Home | `/` | Platform KPI dashboard with aggregate metrics |
| Stores | `/stores` | Store list with creation |
| Billing | `/billing` | Subscription management |
| Settings | `/settings` | Account settings |

### Store Mode (scoped to a store)
| Page | Path | Description |
|------|------|-------------|
| Store Overview | `/stores/[id]` | Store KPIs, recent orders, quick actions |
| Products | `/stores/[id]/products` | Product CRUD with variants |
| Orders | `/stores/[id]/orders` | Order management with status updates |
| Fulfillment | `/stores/[id]/fulfillment` | Fulfillment tracking |
| Customers | `/stores/[id]/customers` | Customer accounts |
| Discounts | `/stores/[id]/discounts` | Discount code management |
| Categories | `/stores/[id]/categories` | Category tree management |
| Suppliers | `/stores/[id]/suppliers` | Supplier management |
| Reviews | `/stores/[id]/reviews` | Product review moderation |
| Analytics | `/stores/[id]/analytics` | Revenue, orders, customer metrics |
| Themes | `/stores/[id]/themes` | Theme engine (11 presets, 13 block types) |
| Gift Cards | `/stores/[id]/gift-cards` | Gift card management |
| Tax | `/stores/[id]/tax` | Tax rate configuration |
| Currency | `/stores/[id]/currency` | Multi-currency settings |
| Domain | `/stores/[id]/domain` | Custom domain management |
| Teams | `/stores/[id]/teams` | Team member invites |
| Notifications | `/stores/[id]/notifications` | Alert center |
| Webhooks | `/stores/[id]/webhooks` | Webhook configuration |
| Segments | `/stores/[id]/segments` | Customer segmentation |
| Upsells | `/stores/[id]/upsells` | Cross-sell/upsell rules |
| A/B Tests | `/stores/[id]/ab-tests` | A/B test management |
| Fraud | `/stores/[id]/fraud` | Fraud detection rules |
| Bulk | `/stores/[id]/bulk` | Bulk import/export |
| Search | `/stores/[id]/search` | Search analytics |
| Exports | `/stores/[id]/exports` | CSV data exports |
| **Services Hub** | `/stores/[id]/services` | AI & Automation (8 service cards) |
| **Service Detail** | `/stores/[id]/services/[name]` | Individual service page |

## Key Files

| File | Purpose |
|------|---------|
| `src/app/layout.tsx` | Root layout with fonts, theme, metadata |
| `src/components/shell.tsx` | App shell (sidebar + content area) |
| `src/components/sidebar.tsx` | Collapsible sidebar with platform/store modes |
| `src/components/top-bar.tsx` | Top navigation bar |
| `src/components/motion.tsx` | Animation primitives |
| `src/lib/api.ts` | API client (fetch wrapper, handles 204, auth tokens) |
| `src/lib/auth.ts` | JWT token management |

## Testing

E2E tests are in `/e2e/tests/dashboard/`:
- 190+ tests across 17 dashboard spec files
- Covers: auth, stores, products, orders, fulfillment, discounts, categories, suppliers,
  gift cards, tax/refunds, teams/webhooks, reviews/analytics, currency/domain, themes,
  billing, seed data verification, Phase 2 Polish features

```bash
# From project root
cd e2e && npx playwright test tests/dashboard/
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## License

Proprietary — All rights reserved.
