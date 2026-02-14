/**
 * Landing page configuration — THE key config file for each service.
 *
 * Every service in the product suite gets its own copy of this file with
 * customized values. The landing page template reads ALL content from here,
 * making it trivial to spin up a new branded landing page by editing a
 * single file.
 *
 * **For Developers:**
 *   - Replace all `{{PLACEHOLDER}}` values with real service data.
 *   - Colors use OKLCH format for perceptual uniformity (matching the
 *     dashboard design system). Hex fallbacks are provided for
 *     environments that don't support OKLCH.
 *   - Font names must be valid Google Fonts identifiers.
 *   - The `icon` field in features uses a simple string key; the
 *     features component maps these to inline SVG icons.
 *
 * **For Project Managers:**
 *   - This is the ONLY file that needs editing per service.
 *   - All sections (hero, features, pricing, etc.) are config-driven.
 *   - Adding a new feature card or pricing tier is a one-line addition.
 *
 * **For QA Engineers:**
 *   - Verify every config value renders correctly on the page.
 *   - Test with very long strings to ensure no layout overflow.
 *   - Check that pricing values display with correct formatting.
 *
 * **For End Users:**
 *   - This config drives everything you see on the landing page:
 *     the headline, feature descriptions, pricing tiers, and branding.
 *
 * @example
 * ```ts
 * // Minimal override for a new service:
 * export const landingConfig = {
 *   name: "DataPulse",
 *   tagline: "Real-time analytics for modern teams",
 *   slug: "datapulse",
 *   // ... rest of config
 * };
 * ```
 */

/** Configuration for a single feature card displayed in the features grid. */
export interface FeatureConfig {
  /** Short feature title (2-5 words recommended). */
  title: string;
  /** Feature description (1-2 sentences). */
  description: string;
  /** Icon key mapped to an SVG in the features component. */
  icon: string;
}

/** Configuration for a single step in the "How it works" section. */
export interface HowItWorksStep {
  /** Step number (1-indexed). */
  step: number;
  /** Step title. */
  title: string;
  /** Step description. */
  description: string;
}

/** Configuration for a pricing tier card. */
export interface PricingTier {
  /** Machine-readable tier ID (e.g. "free", "pro", "enterprise"). */
  tier: string;
  /** Display name for the tier. */
  name: string;
  /** Monthly price in USD. 0 means free, -1 means "Contact us". */
  price: number;
  /** Whether this tier should be visually highlighted as the recommended option. */
  popular?: boolean;
  /** List of features included in this tier. */
  features: string[];
  /** CTA button text. */
  cta: string;
}

/** Configuration for a stat displayed in the social proof bar. */
export interface StatConfig {
  /** The stat value (e.g. "10K+", "99.9%"). */
  value: string;
  /** Label describing the stat. */
  label: string;
}

/** Complete landing page configuration. */
export interface LandingConfig {
  name: string;
  tagline: string;
  description: string;
  slug: string;
  dashboardUrl: string;
  colors: {
    primary: string;
    primaryHex: string;
    accent: string;
    accentHex: string;
    background: string;
    backgroundHex: string;
  };
  fonts: {
    heading: string;
    body: string;
  };
  hero: {
    headline: string;
    subheadline: string;
    cta: string;
    secondaryCta: string;
  };
  features: FeatureConfig[];
  howItWorks: HowItWorksStep[];
  pricing: PricingTier[];
  stats: StatConfig[];
}

export const landingConfig: LandingConfig = {
  /* ── Branding ── */
  name: "SpyDrop",
  tagline: "Competitor Intelligence",
  description: "Monitor competitor stores in real-time. Track new products, price changes, and inventory levels. Find original suppliers with reverse source matching.",
  slug: "spydrop",
  dashboardUrl: "http://localhost:3105",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.60 0.15 220)",
    primaryHex: "#06b6d4",
    accent: "oklch(0.70 0.12 210)",
    accentHex: "#67e8f9",
    background: "oklch(0.14 0.02 230)",
    backgroundHex: "#0c1826",
  },

  /* ── Typography ── */
  fonts: {
    heading: "Geist",
    body: "Geist",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Know What Your Competitors Do Before They Do It",
    subheadline: "Real-time competitor monitoring that tracks product launches, price changes, and stock levels \u2014 with AI-powered reverse source finding.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "Store Monitoring",
      description: "Add any competitor store URL and automatically track every product they add, remove, or change.",
      icon: "zap",
    },
    {
      title: "Price Tracking",
      description: "Get full price history charts for every competitor product. Spot trends, markdowns, and pricing strategies.",
      icon: "chart",
    },
    {
      title: "Source Finding",
      description: "Reverse-match competitor products to original suppliers on AliExpress, 1688, and other wholesale platforms.",
      icon: "shield",
    },
    {
      title: "Smart Alerts",
      description: "Instant notifications when competitors drop prices, launch new products, or go out of stock.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    {
      step: 1,
      title: "Add Competitors",
      description: "Paste any competitor store URL. SpyDrop begins cataloging their entire product line within minutes.",
    },
    {
      step: 2,
      title: "Auto-Scan & Track",
      description: "Our scanners monitor products, prices, and inventory levels daily — surfacing every change automatically.",
    },
    {
      step: 3,
      title: "Get Alerts & Sources",
      description: "Receive instant alerts on price drops and new products, plus AI-matched supplier links for every item.",
    },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "3 competitor stores",
        "Weekly scans",
        "Basic product tracking",
        "No alerts",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      popular: true,
      features: [
        "25 competitor stores",
        "Daily scans",
        "Price drop & new product alerts",
        "Reverse source finding",
        "Full price history",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 99,
      features: [
        "Unlimited competitor stores",
        "Hourly scans",
        "All features + API access",
        "Bulk source finding",
        "Priority support",
      ],
      cta: "Go Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "100K+", label: "Stores Tracked" },
    { value: "5M+", label: "Products Monitored" },
    { value: "24/7", label: "Scanning" },
  ],
};
