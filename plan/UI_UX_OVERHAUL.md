# UI/UX Overhaul & Store Theme Engine

> **Feature scope:** Full visual redesign of the dashboard, a dynamic per-store theme engine for storefronts,
> and a dashboard theme editor that lets store owners customize every aspect of their store's appearance.
> This document covers the design system, data model, API surface, implementation phases, file inventory,
> and testing strategy. Written for developers, project managers, QA engineers, and end users (store owners).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design System](#2-design-system)
3. [Dashboard UI Overhaul (Part A)](#3-dashboard-ui-overhaul-part-a)
4. [Store Theme Engine — Backend (Part B)](#4-store-theme-engine--backend-part-b)
5. [Storefront Theme Rendering (Part C)](#5-storefront-theme-rendering-part-c)
6. [Dashboard Theme Editor (Part D)](#6-dashboard-theme-editor-part-d)
7. [Implementation Phases & Order](#7-implementation-phases--order)
8. [File Inventory](#8-file-inventory)
9. [Testing Strategy](#9-testing-strategy)
10. [AI Readiness](#10-ai-readiness)
11. [Glossary](#11-glossary)

---

## 1. Executive Summary

### What this feature is about

This initiative is a **complete visual overhaul** of the platform, comprising three interconnected workstreams:

1. **Dashboard overhaul** — Replace the generic Geist-font, gray-scale dashboard with a premium design system featuring distinctive typography, an OKLCH color palette, a collapsible sidebar navigation, light/dark mode, and motion throughout every page.
2. **Storefront theme engine** — Build a backend-driven theme system that lets each store have its own colors, fonts, styles, and homepage block layout. Seven curated preset themes ship out of the box, and store owners can create unlimited custom themes.
3. **Dashboard theme editor** — A visual editor inside the dashboard where store owners pick colors, fonts, styles, and arrange homepage blocks with a live preview.

### Why it matters

| Stakeholder | Value |
|-------------|-------|
| **Store owner** | Professional-looking storefronts differentiate their brand from the "template look" that plagues dropshipping stores. Customization without touching code. |
| **Platform (revenue)** | Theme customization is a Growth/Pro tier feature that justifies premium pricing. A polished dashboard reduces churn and increases user trust. |
| **Developer** | A design system with tokens, shared components, and motion primitives accelerates future feature development. |
| **AI readiness** | The structured JSON theme format is designed so the upcoming Automation AI service (Phase 2) can auto-generate themes based on product niche or brand guidelines. |

### Scope at a glance

| Area | Scope |
|------|-------|
| Dashboard | New design system, sidebar nav, 27 pages updated, auth page redesign, 3 enhanced Shadcn components |
| Backend | New `StoreTheme` model, 6 API endpoints, 7 preset themes seeded, public theme API |
| Storefront | Dynamic Google Fonts, CSS variable injection, 9 block components, theme-aware layout |
| Dashboard editor | Theme gallery, visual customizer (colors, fonts, styles), block manager, live preview |

### What exists today

- The `Store` model already has `theme` (string name), `logo_url`, `favicon_url`, and `custom_css` columns (migration done).
- The dashboard has a basic themes page at `stores/[id]/themes/` that shows 6 theme name buttons.
- However, the backend schemas do not expose theme fields, the storefront never reads them, there is no block system, and there is no rich theme configuration.

---

## 2. Design System

This section defines the visual language used across the **dashboard** (fixed design) and serves as the foundation for the "Frosted" default theme on storefronts.

### 2.1 Typography

| Role | Font Family | Source | Weight(s) | Usage |
|------|-------------|--------|-----------|-------|
| Headings | **Bricolage Grotesque** | Google Fonts | 600, 700 | Page titles, card headings, sidebar section labels |
| Body | **Instrument Sans** | Google Fonts | 400, 500, 600 | Body text, table cells, form labels, buttons |
| Code / Mono | **IBM Plex Mono** | Google Fonts | 400, 500 | Code snippets, API keys, discount codes, JSON previews |

**Why these fonts?** They are distinctive without being trendy. Bricolage Grotesque has optical sizing and character that separates the dashboard from generic SaaS tools. Instrument Sans is highly legible at small sizes. IBM Plex Mono is a proven code font with excellent glyph coverage.

Fonts are loaded via `next/font/google` in the root layout and exposed as CSS variables:

```css
--font-heading: 'Bricolage Grotesque', sans-serif;
--font-body: 'Instrument Sans', sans-serif;
--font-mono: 'IBM Plex Mono', monospace;
```

### 2.2 Color System

Colors use the **OKLCH** color space for perceptually uniform lightness across hues. This means a "50% lightness teal" and a "50% lightness amber" actually look equally bright to the human eye, unlike HSL.

#### "Frosted Glass" Light Mode

| Token | OKLCH Value | Description |
|-------|-------------|-------------|
| `--background` | `oklch(0.985 0.002 80)` | Warm off-white (not paper-white) |
| `--foreground` | `oklch(0.205 0.015 270)` | Near-black with faint blue undertone |
| `--primary` | `oklch(0.55 0.15 195)` | **Teal** — the signature color |
| `--primary-foreground` | `oklch(0.985 0.002 80)` | White text on primary |
| `--accent` | `oklch(0.75 0.15 75)` | **Amber** — warm accent |
| `--accent-foreground` | `oklch(0.25 0.04 75)` | Dark text on amber |
| `--muted` | `oklch(0.94 0.005 80)` | Subtle backgrounds |
| `--muted-foreground` | `oklch(0.55 0.01 270)` | Secondary text |
| `--card` | `oklch(0.995 0.001 80)` | Card background |
| `--border` | `oklch(0.90 0.005 80)` | Subtle borders |
| `--destructive` | `oklch(0.55 0.2 25)` | Error red |
| `--ring` | `oklch(0.55 0.15 195)` | Focus rings (teal) |

#### "Obsidian" Dark Mode

| Token | OKLCH Value | Description |
|-------|-------------|-------------|
| `--background` | `oklch(0.145 0.015 270)` | Navy-black |
| `--foreground` | `oklch(0.93 0.005 80)` | Off-white |
| `--primary` | `oklch(0.70 0.15 195)` | Brighter teal for dark backgrounds |
| `--accent` | `oklch(0.80 0.15 75)` | Golden amber |
| `--muted` | `oklch(0.22 0.015 270)` | Slightly lighter dark |
| `--muted-foreground` | `oklch(0.65 0.01 270)` | Dimmed text |
| `--card` | `oklch(0.185 0.015 270)` | Slightly elevated dark |
| `--border` | `oklch(0.27 0.015 270)` | Subtle dark borders |

All colors are defined as CSS custom properties in `globals.css` and toggled via the `dark` class managed by `next-themes`.

### 2.3 Motion

**Library:** `motion` (the lightweight successor to Framer Motion, 18KB gzip).

| Pattern | Implementation | Where Used |
|---------|---------------|------------|
| **Staggered reveals** | `FadeIn` + `StaggerChildren` wrappers with `animation-delay` | Card grids, table rows, page sections |
| **Hover lift** | `whileHover={{ y: -2 }}` | Cards, sidebar nav items |
| **Press scale** | `whileTap={{ scale: 0.97 }}` | Buttons, interactive cards |
| **Page fade-in** | `initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}` | Every page content area |
| **Theme transition** | `transition: color 200ms, background-color 200ms` on `html` | Light/dark toggle |

Motion is always **opt-in** via wrapper components (`<FadeIn>`, `<StaggerChildren>`). No global animation overrides. Respects `prefers-reduced-motion`.

### 2.4 Background Patterns

| Pattern | Where Used | CSS |
|---------|-----------|-----|
| **Dot grid** | Dashboard main content area (subtle) | `radial-gradient(circle, var(--border) 1px, transparent 1px)` at `24px 24px` |
| **Gradient mesh** | Auth pages (login, register) | `radial-gradient(ellipse at 20% 50%, oklch(0.55 0.15 195 / 0.15), transparent 50%), radial-gradient(ellipse at 80% 50%, oklch(0.75 0.15 75 / 0.1), transparent 50%)` |

### 2.5 Shadcn Component Enhancements

| Component | Enhancement |
|-----------|-------------|
| `Button` | Add `active:scale-[0.97]` transition on all variants. New `accent` variant (amber background). |
| `Card` | New `glass` variant: `bg-card/80 backdrop-blur-sm border-border/50`. |
| `Badge` | New `success` (green) and `warning` (amber) variants alongside existing `default`, `secondary`, `destructive`, `outline`. |

---

## 3. Dashboard UI Overhaul (Part A)

> **Audience note — Project Manager:** This is the visual redesign of the internal admin dashboard that store owners use. It does not change any business logic or data — only the appearance and navigation structure. Every existing page continues to work; they just look better.

### 3.1 Shell Architecture

The dashboard gains a persistent shell around all store-scoped pages:

```
+--[ Sidebar ]--+-------[ Top Bar (breadcrumbs + user menu) ]--------+
|               |                                                     |
| [Logo]        |  Home > Stores > My Store > Products                |
|               |                                                     |
| Commerce      |  +-----------------------------------------------+  |
|   Products    |  |                                                 |  |
|   Orders      |  |  [ Page Content ]                              |  |
|   Discounts   |  |                                                 |  |
|   Gift Cards  |  |                                                 |  |
|               |  |                                                 |  |
| Customers     |  |                                                 |  |
|   Customer List|  |                                                 |  |
|   Segments    |  |                                                 |  |
|   Reviews     |  |                                                 |  |
|               |  +-----------------------------------------------+  |
| Marketing     |                                                     |
|   Upsells     |                                                     |
|   A/B Tests   |                                                     |
|   Email       |                                                     |
|               |                                                     |
| Operations    |                                                     |
|   Suppliers   |                                                     |
|   Fulfillment |                                                     |
|   Analytics   |                                                     |
|   Fraud       |                                                     |
|   Bulk Ops    |                                                     |
|               |                                                     |
| Settings      |                                                     |
|   Store       |                                                     |
|   Themes      |                                                     |
|   Domains     |                                                     |
|   Tax         |                                                     |
|   Currency    |                                                     |
|   Webhooks    |                                                     |
|   Team        |                                                     |
|   Billing     |                                                     |
|               |                                                     |
| [Collapse]    |                                                     |
| [Theme Toggle]|                                                     |
+---------------+-----------------------------------------------------+
```

**Sidebar behavior:**
- Expanded: icon + label (240px width)
- Collapsed: icon-only (64px width), triggered by toggle button at bottom
- Active page indicated by teal left border bar
- Grouped sections with muted section labels (Commerce, Customers, Marketing, Operations, Settings)
- Theme toggle (sun/moon) in sidebar footer
- Collapses automatically on mobile (hamburger menu)

**Top bar:**
- Breadcrumb navigation (auto-generated from route)
- User avatar + dropdown (profile, billing, logout)
- Notification bell (existing Feature 25)

### 3.2 New Components

| Component | File | Purpose |
|-----------|------|---------|
| `Sidebar` | `components/sidebar.tsx` | Collapsible sidebar with grouped nav, lucide icons, active state, theme toggle |
| `DashboardShell` | `components/dashboard-shell.tsx` | Sidebar + main content wrapper with top bar |
| `ThemeToggle` | `components/theme-toggle.tsx` | Sun/Moon toggle using `next-themes` |
| `Breadcrumb` | `components/breadcrumb.tsx` | Auto-breadcrumb from route segments |
| `FadeIn` | `components/motion-wrappers.tsx` | Motion fade-in animation wrapper |
| `StaggerChildren` | `components/motion-wrappers.tsx` | Staggered animation container |
| `Skeleton` | `components/ui/skeleton.tsx` | Shimmer skeleton loader |
| `EmptyState` | `components/empty-state.tsx` | Icon + title + CTA for empty lists |
| `StoreContext` | `contexts/store-context.tsx` | Current store context for sidebar nav |

### 3.3 Page Updates (27 pages)

> **Audience note — QA Engineer:** All 25 store sub-pages plus the home page and stores list page need visual verification after the overhaul. The changes are cosmetic (remove inline headers, add skeletons, add motion), so functional behavior should remain identical. Test each page in both light and dark mode.

**All 25 store sub-pages:**
- Remove inline `<header>` breadcrumb blocks (the shell now handles breadcrumbs)
- Remove `min-h-screen` wrappers (the shell provides the full-height layout)
- Replace loading spinners (`Loader2` icons) with `Skeleton` components
- Wrap page content in `<FadeIn>` motion wrapper
- Wrap card grids in `<StaggerChildren>` for staggered entrance animation

**Auth pages** (`login/page.tsx`, `register/page.tsx`):
- Auth layout gets gradient mesh background
- Login/register cards get glass-morphism treatment: `bg-card/80 backdrop-blur-sm`
- Cards animated with `FadeIn` on mount

**Home + Stores list pages:**
- Same updates as store sub-pages (skeleton, motion, remove inline headers)

### 3.4 Store Layout

A new layout file wraps all `stores/[id]/*` routes:

```
dashboard/src/app/stores/[id]/layout.tsx
```

This layout:
1. Fetches the current store data (name, slug)
2. Provides `StoreContext` to all child pages
3. Renders `<DashboardShell>` with the sidebar and top bar
4. Passes the current store to the sidebar for navigation links

---

## 4. Store Theme Engine — Backend (Part B)

> **Audience note — Developer:** This section defines the data model, API contract, and business logic for the theme engine. All endpoints are store-scoped and require authentication. The theme service handles preset seeding, activation logic, and block validation.

### 4.1 Data Model — `StoreTheme`

**Table name:** `store_themes`

```python
class StoreTheme(Base):
    """
    Represents a visual theme configuration for a store.

    Each store can have multiple themes (presets + custom). Exactly one theme
    is active per store at any time. Preset themes are read-only system themes
    that are cloned when a store owner wants to customize them.

    Parameters:
        id: UUID primary key
        store_id: Foreign key to stores table
        name: Display name (e.g. "Frosted", "My Custom Theme")
        is_active: Whether this is the currently active theme for the store
        is_preset: True for system presets (read-only, cannot be deleted)
        colors: JSON dict of color tokens (primary, secondary, accent, etc.)
        typography: JSON dict of font choices (heading_font, body_font, etc.)
        styles: JSON dict of style options (border_radius, card_style, etc.)
        blocks: JSON array of homepage block configurations
        logo_url: Optional store logo URL
        favicon_url: Optional favicon URL
        custom_css: Optional raw CSS overrides
        created_at: Timestamp of creation
        updated_at: Timestamp of last update

    Returns:
        StoreTheme instance
    """
    __tablename__ = "store_themes"

    id: Mapped[UUID]            # PK
    store_id: Mapped[UUID]      # FK → stores.id
    name: Mapped[str]           # "Frosted", "Midnight", "My Theme"
    is_active: Mapped[bool]     # One active per store
    is_preset: Mapped[bool]     # System preset = read-only

    # JSON columns
    colors: Mapped[dict]        # See color schema below
    typography: Mapped[dict]    # See typography schema below
    styles: Mapped[dict]        # See styles schema below
    blocks: Mapped[list]        # Ordered array of block configs

    logo_url: Mapped[str | None]
    favicon_url: Mapped[str | None]
    custom_css: Mapped[str | None]

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

#### `colors` JSON Schema

```json
{
  "primary": "#0d9488",
  "secondary": "#64748b",
  "accent": "#d4a853",
  "background": "#faf9f7",
  "foreground": "#1a1a2e",
  "muted": "#f1f0ee",
  "border": "#e5e4e2",
  "destructive": "#dc2626",
  "card": "#ffffff",
  "card_foreground": "#1a1a2e",
  "primary_foreground": "#ffffff"
}
```

All colors are stored as hex strings for maximum compatibility. Conversion to OKLCH or HSL happens on the frontend.

#### `typography` JSON Schema

```json
{
  "heading_font": "Bricolage Grotesque",
  "body_font": "Instrument Sans",
  "mono_font": "IBM Plex Mono",
  "heading_weight": "700"
}
```

#### `styles` JSON Schema

```json
{
  "border_radius": "md",
  "card_style": "elevated",
  "button_style": "rounded"
}
```

| Field | Options | Description |
|-------|---------|-------------|
| `border_radius` | `sm` (4px), `md` (8px), `lg` (16px) | Global corner radius |
| `card_style` | `flat`, `elevated`, `glass` | Product card treatment |
| `button_style` | `rounded`, `pill`, `square` | Button shape |

### 4.2 Block System

The homepage of each store is composed of an ordered list of **blocks**. There are 9 fixed block types — store owners cannot create new types, but they can add, remove, reorder, enable/disable, and configure any of the 9 types.

| Block Type | Description | Configurable Options |
|------------|-------------|---------------------|
| `hero_banner` | Full-width hero with title, subtitle, and CTA button | `title`, `subtitle`, `cta_text`, `cta_link`, `bg_type` (gradient\|image\|solid), `bg_value`, `text_align` |
| `featured_products` | Grid of featured products | `title`, `count` (4\|8\|12), `columns` (2\|3\|4), `show_prices`, `show_badges` |
| `categories_grid` | Grid of category cards | `title`, `columns` (2\|3\|4), `show_product_count` |
| `product_carousel` | Horizontal scrolling product cards | `title`, `source` (latest\|bestselling), `count` |
| `reviews` | Customer reviews showcase | `title`, `count`, `layout` (grid\|carousel) |
| `newsletter` | Email signup form | `title`, `subtitle`, `button_text` |
| `custom_text` | Rich text content area | `content` (markdown), `text_align` |
| `image_banner` | Full-width image with optional link | `image_url`, `alt_text`, `link`, `height` (sm\|md\|lg) |
| `spacer` | Vertical whitespace | `height` (sm\|md\|lg\|xl) |

**Block config structure** (inside the `blocks` JSON array):

```json
[
  {
    "id": "block-1",
    "type": "hero_banner",
    "enabled": true,
    "config": {
      "title": "Welcome to My Store",
      "subtitle": "Discover trending products",
      "cta_text": "Shop Now",
      "cta_link": "/products",
      "bg_type": "gradient",
      "bg_value": "linear-gradient(135deg, var(--primary), var(--accent))",
      "text_align": "center"
    }
  },
  {
    "id": "block-2",
    "type": "featured_products",
    "enabled": true,
    "config": {
      "title": "Featured Products",
      "count": 8,
      "columns": 4,
      "show_prices": true,
      "show_badges": true
    }
  }
]
```

### 4.3 Curated Font Library

Store owners choose from a curated list of Google Fonts that are tested for quality, readability, and loading performance. This prevents font-related rendering issues and keeps load times predictable.

**Heading Fonts (12):**

| Font | Style | Best For |
|------|-------|----------|
| Bricolage Grotesque | Geometric sans with character | Modern, tech, general |
| Fraunces | Old-style with optical size | Organic, botanical, artisan |
| Playfair Display | High-contrast serif | Luxury, fashion, premium |
| Syne | Variable grotesque | Futuristic, bold, editorial |
| Outfit | Clean geometric | Friendly, approachable |
| DM Serif Display | Refined serif | Elegant, editorial |
| Unbounded | Bold extended sans | Loud, energetic, youth |
| Archivo Black | Condensed heavy | Industrial, bold statements |
| Cormorant Garamond | Light elegant serif | Sophisticated, literary |
| Josefin Sans | Geometric vintage | Retro, clean, Scandinavian |
| Bitter | Slab serif | Readable, warm, editorial |
| Libre Baskerville | Classic Baskerville | Traditional, trustworthy |

**Body Fonts (8):**

| Font | Style | Best For |
|------|-------|----------|
| Instrument Sans | Humanist sans | General purpose, highly legible |
| Source Sans 3 | Adobe's open sans | Technical, professional |
| Nunito | Rounded sans | Friendly, playful |
| Lora | Contemporary serif | Long-form, editorial |
| Work Sans | Geometric sans | Clean, modern |
| DM Sans | Geometric sans | Minimal, modern |
| Karla | Grotesque sans | Compact, efficient |
| Crimson Text | Book serif | Luxurious, literary |

### 4.4 API Endpoints

**Base path:** `/api/v1/stores/{store_id}/themes`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/` | List all themes for a store (presets + custom) | Store owner |
| `POST` | `/` | Create a new custom theme (optionally clone from a preset) | Store owner |
| `GET` | `/{theme_id}` | Get theme detail including full config | Store owner |
| `PATCH` | `/{theme_id}` | Update theme config (colors, typography, styles, blocks) | Store owner |
| `DELETE` | `/{theme_id}` | Delete a custom theme (cannot delete presets) | Store owner |
| `POST` | `/{theme_id}/activate` | Set this theme as the active theme for the store | Store owner |

**Public endpoint** (no auth required):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/public/stores/{slug}/theme` | Get the active theme config for a store (used by storefront) |

**Request/Response schemas:**

```python
# backend/app/schemas/theme.py

class ThemeCreate(BaseModel):
    """
    Schema for creating a new custom theme.

    Parameters:
        name: Display name for the theme
        clone_from: Optional theme ID to clone config from
        colors: Optional color overrides
        typography: Optional typography overrides
        styles: Optional style overrides
        blocks: Optional block configuration
    """
    name: str
    clone_from: UUID | None = None
    colors: dict | None = None
    typography: dict | None = None
    styles: dict | None = None
    blocks: list | None = None

class ThemeUpdate(BaseModel):
    """
    Schema for updating an existing theme.
    All fields optional — only provided fields are updated.
    """
    name: str | None = None
    colors: dict | None = None
    typography: dict | None = None
    styles: dict | None = None
    blocks: list | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    custom_css: str | None = None

class ThemeResponse(BaseModel):
    """Full theme response including all config."""
    id: UUID
    store_id: UUID
    name: str
    is_active: bool
    is_preset: bool
    colors: dict
    typography: dict
    styles: dict
    blocks: list
    logo_url: str | None
    favicon_url: str | None
    custom_css: str | None
    created_at: datetime
    updated_at: datetime

class PublicThemeResponse(BaseModel):
    """Public-facing theme response (no internal IDs)."""
    name: str
    colors: dict
    typography: dict
    styles: dict
    blocks: list
    logo_url: str | None
    favicon_url: str | None
    custom_css: str | None
```

**Activation logic:**
- When `POST /{theme_id}/activate` is called, the service sets `is_active = False` on all other themes for the store, then sets `is_active = True` on the target theme.
- Only one theme can be active per store at any time.
- Preset themes can be activated directly (they are not cloned on activation).

### 4.5 Seven Preset Themes

> **Audience note — End User (Store Owner):** These are the 7 ready-to-use themes that come with your store. You can activate any of them instantly, or clone one and customize it to match your brand.

Each preset includes a complete color palette, typography pairing, style options, and a default block layout.

#### 1. Frosted (Default)

The default theme for all new stores. Warm, professional, and approachable.

| Property | Value |
|----------|-------|
| **Background** | Warm off-white (`#faf9f7`) |
| **Primary** | Teal (`#0d9488`) |
| **Accent** | Amber (`#d4a853`) |
| **Heading font** | Bricolage Grotesque |
| **Body font** | Instrument Sans |
| **Border radius** | `md` (8px) |
| **Card style** | Elevated |
| **Button style** | Rounded |

#### 2. Midnight

Bold and futuristic. Dark background with bright accents.

| Property | Value |
|----------|-------|
| **Background** | Navy-black (`#0f172a`) |
| **Primary** | Cyan (`#06b6d4`) |
| **Accent** | Silver (`#94a3b8`) |
| **Heading font** | Syne |
| **Body font** | Instrument Sans |
| **Border radius** | `sm` (4px) |
| **Card style** | Glass |
| **Button style** | Square |

#### 3. Botanical

Organic and earthy. Inspired by nature and artisan craftsmanship.

| Property | Value |
|----------|-------|
| **Background** | Cream (`#fef9ef`) |
| **Primary** | Forest green (`#166534`) |
| **Accent** | Terracotta (`#c2774b`) |
| **Heading font** | Fraunces |
| **Body font** | Lora |
| **Border radius** | `lg` (16px) |
| **Card style** | Flat |
| **Button style** | Rounded |

#### 4. Neon

High-energy and loud. For stores targeting younger audiences.

| Property | Value |
|----------|-------|
| **Background** | Near-black (`#0a0a0a`) |
| **Primary** | Magenta (`#e11d9b`) |
| **Accent** | Lime (`#84cc16`) |
| **Heading font** | Unbounded |
| **Body font** | DM Sans |
| **Border radius** | `sm` (4px) |
| **Card style** | Flat |
| **Button style** | Square |

#### 5. Luxe

Sophisticated and premium. For high-end or fashion-oriented stores.

| Property | Value |
|----------|-------|
| **Background** | Ivory (`#fffff5`) |
| **Primary** | Deep gold (`#b8860b`) |
| **Accent** | Black (`#1a1a1a`) |
| **Heading font** | Playfair Display |
| **Body font** | Crimson Text |
| **Border radius** | `sm` (4px) |
| **Card style** | Elevated |
| **Button style** | Pill |

#### 6. Playful

Bright, colorful, and approachable. For lifestyle and casual stores.

| Property | Value |
|----------|-------|
| **Background** | White (`#ffffff`) |
| **Primary** | Coral (`#f43f5e`) |
| **Accent** | Sky blue (`#38bdf8`) |
| **Heading font** | Outfit |
| **Body font** | Nunito |
| **Border radius** | `lg` (16px) |
| **Card style** | Elevated |
| **Button style** | Pill |

#### 7. Industrial

Raw and utilitarian. For tools, tech, or minimalist stores.

| Property | Value |
|----------|-------|
| **Background** | Light gray (`#f4f4f5`) |
| **Primary** | Charcoal (`#27272a`) |
| **Accent** | Rust (`#c2410c`) |
| **Heading font** | Archivo Black |
| **Body font** | Work Sans |
| **Border radius** | `sm` (4px) |
| **Card style** | Flat |
| **Button style** | Square |

### 4.6 Database Migration

A new Alembic migration creates the `store_themes` table and seeds all 7 preset themes for every existing store. New stores created after the migration will have presets seeded automatically by the theme service on store creation.

### 4.7 Backend Tests

New test file: `backend/tests/test_themes.py`

| Test Case | Description |
|-----------|-------------|
| `test_list_themes` | Returns 7 presets for a new store |
| `test_create_custom_theme` | Creates a custom theme with full config |
| `test_create_theme_clone_from_preset` | Clones a preset and allows modification |
| `test_update_theme` | Partial update of colors/typography/styles/blocks |
| `test_delete_custom_theme` | Deletes a custom theme |
| `test_delete_preset_theme_fails` | Cannot delete a system preset |
| `test_activate_theme` | Activates a theme and deactivates the previous one |
| `test_only_one_active_theme` | Confirms only one theme is active at any time |
| `test_public_theme_endpoint` | Returns active theme by store slug |
| `test_public_theme_no_auth_required` | Public endpoint works without JWT |

---

## 5. Storefront Theme Rendering (Part C)

> **Audience note — Project Manager:** This is where the theme engine becomes visible to store customers. The storefront dynamically loads colors, fonts, and homepage blocks from the theme API. No hardcoded designs — everything is data-driven.

### 5.1 Theme Loading Flow

```
1. Customer visits store URL (e.g., mystore.platform.com)
2. Storefront layout.tsx fetches GET /api/v1/public/stores/{slug}/theme
3. Response contains: colors, typography, styles, blocks, logo, favicon
4. Layout injects:
   a. <link> tag for Google Fonts (heading + body + mono fonts)
   b. CSS custom properties on <body> from theme colors
   c. Font family variables from theme typography
5. Homepage renders blocks in order via <BlockRenderer>
6. All components read CSS variables for colors and fonts
```

### 5.2 Dynamic Google Fonts Loading

```typescript
// storefront/src/lib/theme-utils.ts

/**
 * Generates a Google Fonts URL for the given theme typography config.
 *
 * Parameters:
 *   typography - Theme typography config with heading_font, body_font, mono_font
 *
 * Returns:
 *   A fully formed Google Fonts CSS URL string
 */
function generateGoogleFontsUrl(typography: ThemeTypography): string {
  const fonts = [
    `${typography.heading_font}:wght@600;700`,
    `${typography.body_font}:wght@400;500;600`,
  ];
  if (typography.mono_font) {
    fonts.push(`${typography.mono_font}:wght@400;500`);
  }
  const families = fonts.map(f => `family=${f.replace(/ /g, '+')}`).join('&');
  return `https://fonts.googleapis.com/css2?${families}&display=swap`;
}
```

### 5.3 CSS Variable Injection

```typescript
/**
 * Converts a theme colors object to CSS custom property assignments
 * that can be applied to the <body> element's style attribute.
 *
 * Parameters:
 *   colors - Theme colors dict (primary, accent, background, etc.)
 *
 * Returns:
 *   A CSS string suitable for the style attribute
 */
function themeToCssVars(colors: ThemeColors): string {
  return Object.entries(colors)
    .map(([key, value]) => `--${key.replace(/_/g, '-')}: ${value}`)
    .join('; ');
}
```

### 5.4 Block Rendering System

```
storefront/src/components/blocks/
  block-renderer.tsx      — Maps block type → component, renders in order
  hero-banner.tsx          — Full-width hero with gradient/image/solid BG
  featured-products.tsx    — Product grid (fetches from API based on count)
  categories-grid.tsx      — Category cards grid
  product-carousel.tsx     — Horizontal scrolling product cards
  reviews-block.tsx        — Customer review cards
  newsletter.tsx           — Email signup form
  custom-text.tsx          — Markdown content rendering
  image-banner.tsx         — Full-width image with optional link
  spacer.tsx               — Vertical spacing element
```

**BlockRenderer logic:**

```typescript
/**
 * Renders an ordered list of homepage blocks based on the theme config.
 * Only renders blocks where enabled === true. Unknown block types are
 * silently skipped (forward-compatible with future block types).
 *
 * Parameters:
 *   blocks - Array of block configurations from the theme
 *   storeSlug - Store slug for data fetching within blocks
 *
 * Returns:
 *   JSX fragment with rendered block components
 */
function BlockRenderer({ blocks, storeSlug }: BlockRendererProps) {
  return (
    <>
      {blocks
        .filter(block => block.enabled)
        .map(block => {
          const Component = BLOCK_COMPONENTS[block.type];
          if (!Component) return null;
          return <Component key={block.id} config={block.config} storeSlug={storeSlug} />;
        })}
    </>
  );
}
```

### 5.5 Theme-Aware Layout Components

| Component | File | Features |
|-----------|------|----------|
| `StoreHeader` | `components/store-header.tsx` | Backdrop-blur header, dynamic logo, nav links, theme toggle, Cmd+K search trigger, cart badge |
| `StoreFooter` | `components/store-footer.tsx` | Multi-column footer, social links, newsletter mini-form, copyright |
| `ThemeToggle` | `components/theme-toggle.tsx` | Sun/Moon toggle (light ↔ dark mode per store) |
| `SearchModal` | `components/search-modal.tsx` | Command-K style full-screen search overlay with keyboard nav |
| `MotionWrappers` | `components/motion-wrappers.tsx` | `FadeIn`, `StaggerChildren` animation primitives |

### 5.6 Component & Page Updates

All existing storefront components and pages are updated to:
- Read colors from CSS variables instead of hardcoded Tailwind classes
- Use theme fonts via CSS variable inheritance
- Add motion (hover lifts on product cards, fade-in on pages)
- Use the new header/footer components

| File | Changes |
|------|---------|
| `product-grid.tsx` | Theme-aware card styling, hover lift animation, staggered grid |
| `add-to-cart.tsx` | Primary color from `var(--primary)`, press scale animation |
| `cart-badge.tsx` | Lucide icon, animated count badge |
| `product-reviews.tsx` | Theme accent for stars, refined layout |
| `product-upsells.tsx` | Theme-aware card design |
| `header-search.tsx` | Simplified to trigger SearchModal on click/Cmd+K |
| `products/[slug]/page.tsx` | Motion fade-in, theme-aware typography |
| `cart/page.tsx` | Glass-morphism summary card, themed checkout button |
| `categories/page.tsx` | Theme-driven accent colors |
| `lib/types.ts` | New `StoreTheme`, `Block`, `BlockConfig` TypeScript interfaces |

---

## 6. Dashboard Theme Editor (Part D)

> **Audience note — End User (Store Owner):** The theme editor is where you customize how your store looks. You can pick from preset themes, change colors and fonts, arrange your homepage layout, and see a live preview of your changes before publishing.

### 6.1 Theme Gallery Page

**Route:** `dashboard/stores/[id]/themes/page.tsx`

This page shows all available themes in a grid layout:
- Each theme displayed as a visual preview card (miniature rendering of the theme's color palette and typography)
- Active theme marked with a teal "Active" badge and border
- Preset themes shown first, then custom themes
- "Create Custom Theme" button that opens a dialog to name the theme and optionally pick a preset to clone from
- Delete button on custom themes (with confirmation dialog)
- One-click "Activate" button on any theme

### 6.2 Theme Customizer Page

**Route:** `dashboard/stores/[id]/themes/[themeId]/page.tsx`

A full-page editor with three panels:

```
+--[ Customizer Sidebar (360px) ]--+--[ Live Preview (remaining) ]------+
|                                   |                                     |
| [Colors]                          |  +-------------------------------+  |
|   Primary:  [##] [picker]        |  | [ Header: Logo + Nav ]        |  |
|   Accent:   [##] [picker]        |  |                               |  |
|   Background: [##] [picker]      |  | [ Hero Banner Block ]         |  |
|   Foreground: [##] [picker]      |  |                               |  |
|   ...                             |  | [ Featured Products Grid ]   |  |
|                                   |  |  [card] [card] [card] [card] |  |
| [Typography]                      |  |                               |  |
|   Heading: [ Dropdown v ]        |  | [ Newsletter Block ]          |  |
|   Body:    [ Dropdown v ]        |  |                               |  |
|   Weight:  [ Dropdown v ]        |  | [ Footer ]                    |  |
|   Preview: "The quick brown..."   |  +-------------------------------+  |
|                                   |                                     |
| [Styles]                          |                                     |
|   Border Radius: [sm] [md] [lg]  |                                     |
|   Card Style: [flat][elev][glass] |                                     |
|   Button Style: [round][pill][sq] |                                     |
|                                   |                                     |
| [Branding]                        |                                     |
|   Logo URL: [_____________]       |                                     |
|   Favicon URL: [___________]      |                                     |
|   Custom CSS: [textarea]          |                                     |
|                                   |                                     |
| [Blocks] (tab)                    |                                     |
|   [drag] Hero Banner [on/off]    |                                     |
|   [drag] Featured Products [on]  |                                     |
|   [drag] Categories Grid [on]    |                                     |
|   [ + Add Block ]                 |                                     |
|                                   |                                     |
| [ Save ]  [ Activate & Publish ] |                                     |
+-----------------------------------+-------------------------------------+
```

**Customizer features:**
- **Color pickers**: Native `<input type="color">` + hex text input. Colors stored as hex.
- **Font selectors**: Dropdowns populated from the curated font library. Preview text updates live.
- **Style selectors**: Visual radio-button groups showing the effect of each option.
- **Block manager**: List of blocks with drag handles (or up/down arrows) for reordering. Click a block to expand its config form. Toggle switch to enable/disable. "Add Block" dropdown to add new block types.
- **Live preview**: Renders a miniature storefront using the current theme config. Updates in real-time as the user makes changes. Uses dummy product/category data.

### 6.3 Preview Component

```
dashboard/src/components/theme-preview.tsx
```

Renders a miniature storefront preview:
- Header with logo placeholder and nav links
- Active blocks rendered with dummy data
- Product cards with placeholder images and prices
- Footer with columns
- Theme CSS variables applied via inline `style` attribute
- Google Fonts loaded via dynamically inserted `<link>` tag
- Not an iframe — rendered inline for immediate responsiveness

### 6.4 Color Picker Component

```
dashboard/src/components/ui/color-picker.tsx
```

A simple, accessible color picker:
- Native `<input type="color">` for the visual picker (no heavy third-party library)
- Hex text input for precise values
- Color swatch preview circle
- Label prop for the color role ("Primary", "Accent", etc.)

---

## 7. Implementation Phases & Order

> **Audience note — Project Manager:** The work is divided into 4 phases (A through D) with 7 steps total. Each step is independently verifiable. The phases are sequential — each depends on the previous one being complete.

| Step | Phase | Scope | Estimated Effort | Dependencies |
|------|-------|-------|-----------------|--------------|
| **1** | A.1–A.2 | Dashboard design system foundation: install deps, add fonts, rewrite `globals.css` color system | Small | None |
| **2** | A.3–A.4 | Dashboard sidebar, shell, shared components (motion wrappers, skeleton, empty state, Shadcn enhancements) | Medium | Step 1 |
| **3** | A.5 | Dashboard page updates: all 27 pages updated with shell, skeleton, motion | Medium | Step 2 |
| **4** | B.1–B.7 | Backend theme engine: model, migration, API, service, presets, tests | Medium | None (can start in parallel with Step 1) |
| **5** | C.1–C.3 | Storefront theme rendering: dependencies, theme provider, dynamic fonts, block components | Medium | Step 4 |
| **6** | C.4–C.6 | Storefront page and component updates: homepage rewrite, layout components, theme-aware styling | Medium | Step 5 |
| **7** | D.1–D.4 | Dashboard theme editor: gallery, customizer, block manager, preview | Large | Steps 3 + 4 |

**Critical path:** Steps 1 → 2 → 3 (dashboard) and Steps 4 → 5 → 6 (backend + storefront) can run in parallel. Step 7 requires both paths to be complete.

```
Timeline (sequential within each track, parallel across tracks):

Track 1 (Dashboard):    [Step 1] → [Step 2] → [Step 3] ─────────────┐
                                                                       ↘
                                                                        [Step 7]
                                                                       ↗
Track 2 (Backend+SF):   [Step 4] → [Step 5] → [Step 6] ─────────────┘
```

### Verification Checkpoints

| After Step | How to Verify |
|------------|---------------|
| 1 | `cd dashboard && npm run build` passes. Fonts and colors visible in browser. |
| 2 | Sidebar renders, collapses, theme toggle works (light ↔ dark). |
| 3 | All 27 pages render without errors. No visual regressions (manual spot-check). |
| 4 | `cd backend && python -m pytest` passes. `GET /api/v1/public/stores/{slug}/theme` returns preset data. |
| 5 | Storefront loads with dynamic fonts and colors from theme API. Block components render. |
| 6 | Full storefront homepage renders blocks. Theme toggle works. All pages themed. |
| 7 | Theme gallery shows presets. Editor allows customization with live preview. Changes persist via API. |

---

## 8. File Inventory

### 8.1 New Files (~40)

#### Dashboard (14 new files)

| File | Purpose |
|------|---------|
| `src/components/sidebar.tsx` | Collapsible sidebar navigation |
| `src/components/dashboard-shell.tsx` | Sidebar + main content shell |
| `src/components/theme-toggle.tsx` | Sun/Moon light/dark toggle |
| `src/components/breadcrumb.tsx` | Auto-breadcrumb from route |
| `src/components/motion-wrappers.tsx` | `FadeIn`, `StaggerChildren` |
| `src/components/ui/skeleton.tsx` | Shimmer skeleton loader |
| `src/components/empty-state.tsx` | Icon + title + CTA empty state |
| `src/components/theme-preview.tsx` | Miniature storefront preview |
| `src/components/ui/color-picker.tsx` | Color input with swatch |
| `src/contexts/store-context.tsx` | Current store React context |
| `src/app/stores/[id]/layout.tsx` | Store-scoped shell layout |
| `src/app/stores/[id]/themes/[themeId]/page.tsx` | Theme editor page |

#### Backend (7 new files)

| File | Purpose |
|------|---------|
| `app/models/theme.py` | `StoreTheme` SQLAlchemy model |
| `app/api/themes.py` | Theme CRUD + activation router |
| `app/schemas/theme.py` | Pydantic request/response schemas |
| `app/services/theme_service.py` | Theme business logic + preset seeding |
| `app/constants/themes.py` | 7 preset theme definitions |
| `alembic/versions/xxx_add_store_themes.py` | Migration for `store_themes` table |
| `tests/test_themes.py` | Theme API tests |

#### Storefront (16 new files)

| File | Purpose |
|------|---------|
| `src/components/blocks/block-renderer.tsx` | Block type → component mapper |
| `src/components/blocks/hero-banner.tsx` | Hero banner block |
| `src/components/blocks/featured-products.tsx` | Featured products grid block |
| `src/components/blocks/categories-grid.tsx` | Categories grid block |
| `src/components/blocks/product-carousel.tsx` | Product carousel block |
| `src/components/blocks/reviews-block.tsx` | Reviews showcase block |
| `src/components/blocks/newsletter.tsx` | Newsletter signup block |
| `src/components/blocks/custom-text.tsx` | Markdown text block |
| `src/components/blocks/image-banner.tsx` | Image banner block |
| `src/components/blocks/spacer.tsx` | Vertical spacer block |
| `src/components/store-header.tsx` | Theme-aware header |
| `src/components/store-footer.tsx` | Theme-aware footer |
| `src/components/theme-toggle.tsx` | Light/dark toggle |
| `src/components/search-modal.tsx` | Command-K search overlay |
| `src/components/motion-wrappers.tsx` | Animation primitives |
| `src/lib/theme-utils.ts` | Font URL generation, CSS var conversion |

### 8.2 Modified Files (~45)

#### Dashboard (~30 modified files)

| File | Change |
|------|--------|
| `package.json` | Add `motion`, `next-themes` |
| `src/app/layout.tsx` | Replace Geist fonts, add `ThemeProvider`, add `Toaster` |
| `src/app/globals.css` | Full rewrite: OKLCH colors, font vars, dot-grid, dark mode |
| `src/components/ui/button.tsx` | Add press scale, `accent` variant |
| `src/components/ui/card.tsx` | Add `glass` variant |
| `src/components/ui/badge.tsx` | Add `success`, `warning` variants |
| `src/app/(auth)/layout.tsx` | Gradient mesh background |
| `src/app/(auth)/login/page.tsx` | Glass card, motion fade-in |
| `src/app/(auth)/register/page.tsx` | Glass card, motion fade-in |
| `src/app/page.tsx` | Remove inline header, add skeleton + motion |
| `src/app/stores/page.tsx` | Remove inline header, add skeleton + motion |
| `src/app/stores/[id]/themes/page.tsx` | Full rewrite: theme gallery |
| *+ 25 store sub-pages* | Remove headers, add skeleton + motion |

#### Backend (~4 modified files)

| File | Change |
|------|--------|
| `app/main.py` | Register themes router |
| `app/models/__init__.py` | Import `StoreTheme` |
| `app/api/public.py` | Add `GET /public/stores/{slug}/theme` |
| `app/schemas/public.py` | Add `PublicThemeResponse` |

#### Storefront (~10 modified files)

| File | Change |
|------|--------|
| `package.json` | Add `motion`, `next-themes`, `lucide-react` |
| `src/app/layout.tsx` | Full rewrite: theme loading, font injection, CSS vars |
| `src/app/globals.css` | Rewrite: base vars, block utilities, transitions |
| `src/app/page.tsx` | Replace hardcoded content with `<BlockRenderer>` |
| `src/components/product-grid.tsx` | Theme-aware cards, hover lift, stagger |
| `src/components/add-to-cart.tsx` | Theme primary color, press animation |
| `src/components/cart-badge.tsx` | Lucide icon, animated count |
| `src/components/product-reviews.tsx` | Theme accent stars |
| `src/components/product-upsells.tsx` | Theme-aware cards |
| `src/components/header-search.tsx` | Trigger for search modal |
| `src/app/products/[slug]/page.tsx` | Motion, theme-aware styling |
| `src/app/cart/page.tsx` | Glass summary, themed button |
| `src/app/categories/page.tsx` | Theme accent colors |
| `src/lib/types.ts` | Add theme TypeScript interfaces |

---

## 9. Testing Strategy

### 9.1 Backend Tests (Automated)

**File:** `backend/tests/test_themes.py`

Uses the existing test infrastructure: `pytest` + `httpx.AsyncClient` + async DB fixtures.

| Category | Test Cases |
|----------|-----------|
| **CRUD** | List themes, create theme, create clone, get detail, update partial, delete custom, reject delete preset |
| **Activation** | Activate theme, verify previous deactivated, verify only-one-active invariant |
| **Public API** | Get active theme by slug, no auth required, 404 when no store |
| **Validation** | Reject invalid block types, reject invalid font names, reject empty theme name |
| **Seeding** | New store gets 7 presets, Frosted is active by default |

**Run:** `cd backend && python -m pytest tests/test_themes.py -v`

### 9.2 Frontend Build Verification (Automated)

```bash
# Dashboard build must pass
cd dashboard && npm run build

# Storefront build must pass
cd storefront && npm run build
```

These verify that all TypeScript types are correct, no missing imports, and no build-time errors. Run as part of CI.

### 9.3 Manual Testing Checklist

> **Audience note — QA Engineer:** Use this checklist for manual verification after each implementation phase. Test in Chrome, Firefox, and Safari. Test at both desktop (1440px) and mobile (375px) widths.

#### Dashboard (Phase A)

- [ ] Sidebar renders with all navigation groups (Commerce, Customers, Marketing, Operations, Settings)
- [ ] Sidebar collapse/expand works (toggle button and mobile hamburger)
- [ ] Active page highlighted with teal bar in sidebar
- [ ] Theme toggle switches between light and dark mode
- [ ] Theme preference persists across page reloads (stored in localStorage)
- [ ] Breadcrumbs update correctly when navigating between pages
- [ ] All 27 pages render without errors in both light and dark mode
- [ ] Skeleton loaders appear briefly before data loads
- [ ] Staggered animations play on card grids (products, orders, etc.)
- [ ] Auth pages (login, register) show gradient mesh background and glass cards
- [ ] Press animation on buttons (subtle scale-down on click)
- [ ] Hover lift on cards (subtle upward movement on hover)
- [ ] No horizontal scrollbar at any viewport width
- [ ] Sidebar collapses to hamburger on mobile (< 768px)

#### Backend (Phase B)

- [ ] `GET /api/v1/stores/{store_id}/themes` returns 7 presets for a new store
- [ ] `POST /api/v1/stores/{store_id}/themes` creates a custom theme
- [ ] Cloning from a preset copies all config correctly
- [ ] `PATCH` updates only the fields provided
- [ ] `DELETE` works for custom themes, returns 403 for presets
- [ ] `POST /activate` switches active theme, deactivates previous
- [ ] `GET /api/v1/public/stores/{slug}/theme` returns active theme without auth
- [ ] All tests pass: `python -m pytest tests/test_themes.py -v`

#### Storefront (Phase C)

- [ ] Storefront loads fonts from Google Fonts based on active theme
- [ ] Colors match the active theme (primary, accent, background visible in header, buttons, cards)
- [ ] Homepage renders blocks in the order defined by the theme
- [ ] Hero banner displays with correct background type (gradient/image/solid)
- [ ] Featured products block fetches and displays correct number of products
- [ ] Categories grid shows categories with product counts
- [ ] Product carousel scrolls horizontally
- [ ] Newsletter block displays signup form
- [ ] Custom text block renders markdown correctly
- [ ] Image banner displays with link
- [ ] Spacer block adds correct vertical space
- [ ] Theme toggle (light/dark) works on storefront
- [ ] Search modal opens with Cmd+K (Mac) or Ctrl+K (Windows)
- [ ] Switching active theme via API changes storefront appearance
- [ ] All 7 preset themes render correctly when activated

#### Theme Editor (Phase D)

- [ ] Theme gallery shows all presets + custom themes
- [ ] Active theme marked with indicator
- [ ] "Create Custom Theme" creates a new theme (with optional clone source)
- [ ] Color pickers update the live preview in real-time
- [ ] Font selectors load the selected Google Font in preview
- [ ] Style selectors (border radius, card style, button style) reflect in preview
- [ ] Block manager shows all blocks with enable/disable toggles
- [ ] Adding a new block updates the preview
- [ ] Removing a block updates the preview
- [ ] Reordering blocks (drag or arrows) updates the preview
- [ ] Per-block config (e.g., hero title, product count) updates the preview
- [ ] "Save" persists changes via API (verify with a page refresh)
- [ ] "Activate & Publish" saves and activates the theme
- [ ] Deleting a custom theme from the gallery works

### 9.4 Responsive Testing

| Breakpoint | Width | What to Check |
|------------|-------|---------------|
| Mobile | 375px | Sidebar hidden (hamburger), single-column blocks, stacked cards |
| Tablet | 768px | Sidebar collapsed by default, 2-column product grids |
| Desktop | 1024px | Sidebar expanded, 3-4 column product grids |
| Wide | 1440px | Max-width container, comfortable spacing |

### 9.5 Cross-Browser Testing

| Browser | Version | Platform |
|---------|---------|----------|
| Chrome | Latest | macOS, Windows |
| Firefox | Latest | macOS, Windows |
| Safari | Latest | macOS |
| Edge | Latest | Windows |
| Chrome Mobile | Latest | Android |
| Safari Mobile | Latest | iOS |

**OKLCH note:** OKLCH is supported in all modern browsers (Chrome 111+, Firefox 113+, Safari 16.4+). No fallback is needed for our target browsers.

---

## 10. AI Readiness

> **Audience note — Developer / Project Manager:** This section explains how the theme engine is designed to work with the future Automation AI service (Phase 2). No AI integration is built now — this documents the design decisions that make future AI integration straightforward.

### 10.1 Structured JSON = AI-Friendly

The entire theme configuration is structured JSON with well-defined schemas:

```json
{
  "colors": { "primary": "#0d9488", "accent": "#d4a853", ... },
  "typography": { "heading_font": "Bricolage Grotesque", "body_font": "Instrument Sans" },
  "styles": { "border_radius": "md", "card_style": "elevated", "button_style": "rounded" },
  "blocks": [
    { "type": "hero_banner", "config": { "title": "...", "bg_type": "gradient" } },
    { "type": "featured_products", "config": { "count": 8, "columns": 4 } }
  ]
}
```

An AI model can generate this JSON directly. No HTML, no CSS, no code generation required.

### 10.2 Curated Options = Safe AI Output

The curated font library (12 headings, 8 body) and fixed style options (`sm|md|lg` for radius, `flat|elevated|glass` for cards) constrain AI output to options that are guaranteed to render correctly. An AI cannot choose a font that does not exist in the library or set a border radius that breaks the layout.

### 10.3 Block System = Composable Layouts

The 9 fixed block types give AI a set of building blocks to compose homepage layouts without generating arbitrary HTML. The AI decides:
- Which blocks to include
- What order to place them in
- What config values to set per block

This is much safer and more predictable than asking AI to generate freeform page layouts.

### 10.4 Future AI Integration Path

When the Automation service (Phase 2) is built, the following capabilities become possible:

| Capability | How It Works |
|------------|-------------|
| **AI theme generation** | User describes their brand ("minimalist tech store with dark aesthetic") → AI generates a full theme JSON → saves via theme API |
| **Niche-based presets** | AI analyzes the store's product niche and recommends or auto-generates a theme that matches the product category (e.g., botanical theme for plant stores) |
| **A/B test themes** | AI creates theme variants and the A/B test system (Feature 29) measures which converts better |
| **Seasonal updates** | AI automatically adjusts theme colors for holidays/seasons (e.g., red/green for winter holidays) |

All of these work through the existing theme API — no changes to the theme engine are needed.

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| **Block** | A configurable homepage section (hero banner, product grid, etc.) defined in the theme's `blocks` array |
| **OKLCH** | A perceptually uniform color space that ensures consistent lightness across hues. Format: `oklch(lightness chroma hue)` |
| **Preset theme** | One of the 7 system-provided themes (Frosted, Midnight, etc.) that cannot be deleted but can be activated or cloned |
| **Custom theme** | A store-owner-created theme, optionally cloned from a preset, that can be fully customized and deleted |
| **Active theme** | The one theme per store that is currently rendered on the storefront |
| **Glass-morphism** | A design effect combining semi-transparent background + backdrop blur to create a "frosted glass" appearance |
| **CSS custom properties** | CSS variables (e.g., `--primary`) that enable dynamic theming without regenerating stylesheets |
| **Shell** | The persistent layout wrapper (sidebar + top bar) around all dashboard store pages |
| **Design system** | The shared set of tokens (colors, fonts, spacing), components, and patterns used consistently across the dashboard |
| **BlockRenderer** | The storefront component that maps block types to React components and renders them in order |
| **Curated font library** | The vetted list of Google Fonts that store owners can choose from in the theme editor |
| **Theme toggle** | The sun/moon button that switches between light and dark mode |

---

## Appendix: Relationship to Existing Features

| Feature | Relationship |
|---------|-------------|
| **F15 (Store Customization & Themes)** | This overhaul replaces and supersedes the basic F15 implementation. The existing `theme` string column on `Store` becomes obsolete — the new `StoreTheme` model replaces it entirely. |
| **F12 (Reviews)** | The `reviews` block type renders review data from the existing reviews API |
| **F9 (Categories)** | The `categories_grid` block type renders categories from the existing categories API |
| **F17 (Search)** | The Command-K search modal replaces the existing search bar component |
| **F29 (A/B Testing)** | Future: theme variants can be A/B tested using the existing testing infrastructure |
| **Phase 2 (Automation AI)** | AI theme generation becomes possible through the structured JSON API — see [AI Readiness](#10-ai-readiness) |
