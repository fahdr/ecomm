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
  name: "SourcePilot",
  tagline: "Automated Supplier Product Import",
  slug: "sourcepilot",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8109",

  colors: {
    primary: "oklch(0.60 0.22 30)",     // OKLCH value, e.g. "oklch(0.55 0.15 195)"
    primaryHex: "#e05a33",    // Fallback hex, e.g. "#0d9488"
    accent: "oklch(0.75 0.18 60)",       // OKLCH value, e.g. "oklch(0.75 0.15 75)"
    accentHex: "#e8a838",      // Fallback hex, e.g. "#f59e0b"
  },

  fonts: {
    heading: "Outfit",      // Google Font family name — AVOID: Inter, Roboto, Arial, Space Grotesk
    body: "DM Sans",            // Google Font family name — AVOID: Inter, Roboto, Arial, system fonts
    // Good heading fonts: Syne, Clash Display, Plus Jakarta Sans, Outfit, Bricolage Grotesque
    // Good body fonts: DM Sans, Nunito Sans, Source Sans 3, Lexend, Manrope, Quicksand, Instrument Sans
  },

  navigation: [
    { label: "Dashboard", href: "/", icon: "LayoutDashboard" },
    { label: "Imports", href: "/imports", icon: "Download" },
    { label: "Products", href: "/products", icon: "Search" },
    { label: "Suppliers", href: "/suppliers", icon: "Building2" },
    { label: "Connections", href: "/connections", icon: "Link" },
    { label: "Price Watch", href: "/price-watch", icon: "TrendingUp" },
    { label: "API Keys", href: "/api-keys", icon: "Key" },
    { label: "Billing", href: "/billing", icon: "CreditCard" },
    { label: "Settings", href: "/settings", icon: "Settings" },
  ],

  plans: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "10 imports/month",
        "1 store connection",
        "AliExpress only",
        "Manual import",
        "Basic product preview",
      ],
    },
    {
      tier: "pro",
      name: "Pro",
      price: 49,
      features: [
        "500 imports/month",
        "10 store connections",
        "All suppliers (AliExpress, CJ, Spocket)",
        "Bulk import via CSV",
        "Auto price sync",
        "Priority support",
      ],
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 199,
      features: [
        "Unlimited imports",
        "Unlimited stores",
        "All suppliers + custom",
        "API access",
        "Dedicated account manager",
        "Custom integrations",
        "SLA guarantee",
      ],
    },
  ],
};
