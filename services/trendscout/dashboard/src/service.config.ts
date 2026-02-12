/**
 * Service configuration — the single source of truth for all branding,
 * navigation, and billing tiers in this dashboard.
 *
 * **For Developers:**
 *   When creating a new service from this template, replace every `{{...}}`
 *   placeholder with the service-specific value. The scaffold script
 *   (`scripts/create-service.sh`) does this automatically.
 *
 *   - `name` / `tagline` — displayed in the sidebar, login page, and page titles.
 *   - `slug` — URL-safe identifier used in API paths and Docker container names.
 *   - `apiUrl` — points to the FastAPI backend for this service (port varies per service).
 *   - `colors` — OKLCH primary/accent with hex fallbacks for non-OKLCH contexts (e.g. favicons).
 *   - `fonts.heading` / `fonts.body` — Google Font family names loaded in layout.tsx.
 *   - `navigation` — drives the sidebar; icon names must match lucide-react exports.
 *   - `plans` — drives the billing page plan cards and feature gates.
 *
 * **For Project Managers:**
 *   This file controls everything a user sees about the service brand.
 *   Changing `name`, `tagline`, or `colors` here updates the entire dashboard.
 *
 * **For QA Engineers:**
 *   - Verify that all navigation items route to real pages.
 *   - Verify that plan features match what the backend enforces.
 *   - Test with different `apiUrl` values (localhost vs production).
 *
 * **For End Users:**
 *   You will never edit this file directly — the dashboard reads it
 *   at build time to display the correct service branding.
 */

/** Shape of a single navigation entry in the sidebar. */
export interface NavItem {
  /** Display label shown in the sidebar link. */
  label: string;
  /** Route path relative to the dashboard root. */
  href: string;
  /** Name of a lucide-react icon component (PascalCase). */
  icon: string;
}

/** Shape of a billing plan tier. */
export interface PlanTier {
  /** Machine-readable tier identifier (e.g. "free", "pro", "enterprise"). */
  tier: string;
  /** Human-readable plan name displayed on the billing page. */
  name: string;
  /** Monthly price in USD (0 = free tier). */
  price: number;
  /** List of feature descriptions shown on the plan card. */
  features: string[];
}

/** Complete service configuration object. */
export interface ServiceConfig {
  name: string;
  tagline: string;
  slug: string;
  apiUrl: string;
  colors: {
    primary: string;
    primaryHex: string;
    accent: string;
    accentHex: string;
  };
  fonts: {
    heading: string;
    body: string;
  };
  navigation: NavItem[];
  plans: PlanTier[];
}

export const serviceConfig: ServiceConfig = {
  name: "TrendScout",
  tagline: "AI-Powered Product Research",
  slug: "trendscout",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8101",

  colors: {
    primary: "oklch(0.65 0.20 250)",     // Electric Blue — vibrant primary for data-driven UI
    primaryHex: "#3b82f6",               // Tailwind blue-500 fallback
    accent: "oklch(0.75 0.15 200)",      // Cyan accent for highlights and hover states
    accentHex: "#38bdf8",               // Tailwind sky-400 fallback
  },

  fonts: {
    heading: "Space Grotesk",            // Geometric sans-serif for a tech/data feel
    body: "Inter",                       // Highly legible body font optimized for UI
  },

  navigation: [
    { label: "Dashboard",  href: "/",           icon: "LayoutDashboard" },
    { label: "Research",   href: "/research",   icon: "Search" },
    { label: "Watchlist",  href: "/watchlist",  icon: "Eye" },
    { label: "Sources",    href: "/sources",    icon: "Database" },
    { label: "History",    href: "/history",    icon: "Clock" },
    { label: "API Keys",   href: "/api-keys",   icon: "Key" },
    { label: "Billing",    href: "/billing",    icon: "CreditCard" },
    { label: "Settings",   href: "/settings",   icon: "Settings" },
  ],

  plans: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "5 research runs per month",
        "2 data sources (AliExpress + Google Trends)",
        "Basic product scoring",
        "25 watchlist items",
      ],
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      features: [
        "50 research runs per month",
        "All 4+ data sources including custom",
        "Full AI-powered analysis",
        "500 watchlist items",
        "API access",
      ],
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 99,
      features: [
        "Unlimited research runs",
        "All sources + API access",
        "Priority AI processing",
        "Unlimited watchlist items",
        "Dedicated support",
      ],
    },
  ],
};
