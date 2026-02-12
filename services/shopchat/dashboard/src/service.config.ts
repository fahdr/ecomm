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
  name: "ShopChat",
  tagline: "AI Shopping Assistant",
  slug: "shopchat",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8108",

  colors: {
    primary: "oklch(0.55 0.20 275)",
    primaryHex: "#6366f1",
    accent: "oklch(0.70 0.18 290)",
    accentHex: "#818cf8",
  },

  fonts: {
    heading: "Outfit",
    body: "Inter",
  },

  navigation: [
    { label: "Dashboard", href: "/", icon: "LayoutDashboard" },
    { label: "Chatbots", href: "/chatbots", icon: "Bot" },
    { label: "Knowledge Base", href: "/knowledge-base", icon: "BookOpen" },
    { label: "Conversations", href: "/conversations", icon: "MessageSquare" },
    { label: "Analytics", href: "/analytics", icon: "BarChart3" },
    { label: "Widget", href: "/widget", icon: "PanelBottomClose" },
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
        "50 conversations/mo",
        "Basic knowledge base (10 pages)",
        "Branding only",
        "Basic analytics",
      ],
    },
    {
      tier: "pro",
      name: "Pro",
      price: 19,
      features: [
        "1,000 conversations/mo",
        "Full catalog sync",
        "Personality + flows",
        "Full analytics",
      ],
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 79,
      features: [
        "Unlimited conversations",
        "Unlimited knowledge + API",
        "White-label",
        "Export + webhooks",
      ],
    },
  ],
};
