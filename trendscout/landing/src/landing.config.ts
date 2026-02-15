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
  name: "TrendScout",
  tagline: "AI-Powered Product Research",
  description:
    "Discover winning products before your competitors with AI-powered research across AliExpress, TikTok, Google Trends, and Reddit. Score, analyze, and import products in minutes.",
  slug: "trendscout",
  dashboardUrl: "http://localhost:3101",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.65 0.20 250)",     // Electric Blue
    primaryHex: "#3b82f6",               // Tailwind blue-500
    accent: "oklch(0.75 0.15 200)",      // Cyan accent
    accentHex: "#38bdf8",               // Tailwind sky-400
    background: "oklch(0.15 0.02 260)",  // Deep navy background
    backgroundHex: "#0f172a",            // Tailwind slate-900
  },

  /* ── Typography ── */
  fonts: {
    heading: "Syne",
    body: "DM Sans",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Discover Winning Products Before Everyone Else",
    subheadline:
      "AI-powered research engine that scans AliExpress, TikTok, Google Trends, and Reddit to find high-margin products with real demand signals.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "Multi-Source Scanning",
      description:
        "Simultaneously scan AliExpress, TikTok, Google Trends, and Reddit for emerging product opportunities with real-time data aggregation.",
      icon: "zap",
    },
    {
      title: "AI Scoring Engine",
      description:
        "Proprietary scoring algorithm evaluates demand signals, competition level, margin potential, and trend velocity to rank every product.",
      icon: "chart",
    },
    {
      title: "Watchlist & Alerts",
      description:
        "Track products and niches with automated alerts when scores change, prices drop, or new competitors enter the market.",
      icon: "shield",
    },
    {
      title: "One-Click Import",
      description:
        "Found a winner? Import product data, images, and supplier info directly into your store with a single click.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    {
      step: 1,
      title: "Set Your Criteria",
      description:
        "Define your target keywords, product categories, price range, and minimum margin thresholds to focus the AI search.",
    },
    {
      step: 2,
      title: "AI Scans Sources",
      description:
        "Our engine scrapes and cross-references AliExpress listings, TikTok viral products, Google Trends data, and Reddit discussions in real time.",
    },
    {
      step: 3,
      title: "Score & Import",
      description:
        "Review a ranked list of products scored by demand, competition, and margin — then import winners to your store with one click.",
    },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
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
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      popular: true,
      features: [
        "50 research runs per month",
        "All 4+ data sources including custom",
        "Full AI-powered analysis",
        "500 watchlist items",
        "API access",
      ],
      cta: "Start Trial",
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
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "25K+", label: "Products Found" },
    { value: "4", label: "Data Sources" },
    { value: "99.9%", label: "Uptime" },
  ],
};
