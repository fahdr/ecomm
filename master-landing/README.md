# Master Landing Page

> The Complete AI Commerce Toolkit

## Overview

The master landing page showcases all 8 SaaS products in the automation suite as a
unified offering. It serves as the top-of-funnel entry point, directing visitors to
individual product landing pages or bundled subscription plans.

**For Developers:**
    This is a static Next.js site (exported with `next export`). All content is
    driven by `src/suite.config.ts` which defines the 8 services, bundle pricing,
    and social proof stats. Components are in `src/components/`.

**For Project Managers:**
    The master landing page showcases the complete product suite. It includes a hero
    section, 8-product grid, how-it-works section, bundle pricing, CTA, and footer.
    Port 3200 in local dev.

**For QA Engineers:**
    Verify all 8 service cards render with correct names, colors, and CTA links.
    Test responsive layout, pricing cards, and navigation links. Check that the
    static export builds without errors.

**For End Users:**
    This is your starting point for exploring the AI commerce toolkit. Browse all
    8 products, compare bundle pricing, and sign up for a free trial.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Landing Page | Next.js 16 (static export) | 3200 |

## Quick Start

```bash
cd services/master-landing
npm install
npm run dev       # → http://localhost:3200
npm run build     # Static export to out/
```

## Page Structure

The landing page is composed of 7 sections, rendered in order:

1. **Navbar** — Logo + navigation links + CTA button
2. **Hero** — Animated headline ("The Complete AI Commerce Toolkit") + subtitle + CTA
3. **Service Grid** — 8 product cards with icons, descriptions, and highlights
4. **How It Works** — 3-step visual process (Choose → Connect → Scale)
5. **Pricing** — 3-tier bundle pricing cards (Starter, Growth, Enterprise)
6. **CTA** — Final call-to-action with gradient background
7. **Footer** — Product links + legal

## Components

| File | Section |
|------|---------|
| `src/components/navbar.tsx` | Top navigation bar |
| `src/components/hero.tsx` | Hero section with animated headline |
| `src/components/service-grid.tsx` | 8-product card grid (reads from suite.config) |
| `src/components/how-it-works.tsx` | 3-step process section |
| `src/components/pricing.tsx` | Bundle pricing cards |
| `src/components/cta.tsx` | Final call-to-action |
| `src/components/footer.tsx` | Footer with links |

## Configuration

All content is driven by `src/suite.config.ts`:

- **`services`** — Array of 8 service configs (name, tagline, description, color, icon, highlights, landingUrl)
- **`suitePricing`** — 3 bundle tiers (Starter $49, Growth $149, Enterprise custom)
- **`suiteStats`** — Social proof numbers (8 tools, 50K+ users, 2M+ tasks, 99.9% uptime)

## Products Showcased

| # | Product | Category | Color |
|---|---------|----------|-------|
| A1 | TrendScout | Research | `#3b82f6` (Blue) |
| A2 | ContentForge | Content | `#a855f7` (Purple) |
| A3 | RankPilot | SEO | `#22c55e` (Green) |
| A4 | FlowSend | Email | `#f59e0b` (Amber) |
| A5 | SpyDrop | Intelligence | `#ef4444` (Red) |
| A6 | PostPilot | Social | `#ec4899` (Pink) |
| A7 | AdScale | Advertising | `#06b6d4` (Cyan) |
| A8 | ShopChat | Support | `#14b8a6` (Teal) |

## License

Proprietary — All rights reserved.
