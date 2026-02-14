/**
 * Landing page configuration for SourcePilot.
 *
 * SourcePilot is a supplier product import automation service that lets users
 * import products from AliExpress, CJDropship, and Spocket, auto-import
 * trending products found by TrendScout, bulk-import from CSV, track supplier
 * prices, and optimize product pricing with markup rules.
 *
 * Every landing page section reads ALL content from this file, making it
 * trivial to rebrand or adjust messaging without touching component code.
 *
 * **For Developers:**
 *   - Colors use OKLCH format for perceptual uniformity with hex fallbacks.
 *   - Font names must be valid Google Fonts identifiers.
 *   - The `icon` field in features maps to inline SVGs in features.tsx.
 *
 * **For Project Managers:**
 *   - This is the ONLY file that needs editing to change landing page content.
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
  /* -- Branding -- */
  name: "SourcePilot",
  tagline: "Automated Supplier Product Import",
  description:
    "Import products from top suppliers in one click. Auto-sync prices, optimize margins, and scale your dropshipping business.",
  slug: "sourcepilot",
  dashboardUrl: "http://localhost:3109",

  /* -- Colors (OKLCH + hex fallbacks) -- */
  colors: {
    primary: "oklch(0.60 0.22 30)",
    primaryHex: "#e05a33",
    accent: "oklch(0.75 0.18 60)",
    accentHex: "#e8a838",
    background: "oklch(0.14 0.03 35)",
    backgroundHex: "#1a1210",
  },

  /* -- Typography -- */
  fonts: {
    heading: "Outfit",
    body: "DM Sans",
  },

  /* -- Hero Section -- */
  hero: {
    headline: "Import Products at Scale",
    subheadline:
      "Connect to AliExpress, CJDropship, and Spocket. Import trending products, sync prices automatically, and optimize your margins with AI-powered pricing.",
    cta: "Start Importing Free",
    secondaryCta: "View Pricing",
  },

  /* -- Features Grid (6 cards) -- */
  features: [
    {
      title: "Multi-Supplier Import",
      description:
        "Import from AliExpress, CJDropship, and Spocket. Paste a URL or search by keyword \u2014 we handle the rest.",
      icon: "download",
    },
    {
      title: "Bulk Operations",
      description:
        "Upload a CSV of product URLs and import hundreds of products in parallel. Perfect for scaling fast.",
      icon: "upload",
    },
    {
      title: "Price Intelligence",
      description:
        "Monitor supplier prices daily. Get alerts on changes and auto-adjust your retail prices to maintain margins.",
      icon: "trending-up",
    },
    {
      title: "Smart Pricing",
      description:
        "Set markup rules per store or category. Psychological pricing rounds to .99 automatically.",
      icon: "dollar-sign",
    },
    {
      title: "Auto-Import Pipeline",
      description:
        "Connect TrendScout to auto-import high-scoring products. Your store grows while you sleep.",
      icon: "zap",
    },
    {
      title: "Content Enhancement",
      description:
        "Imported products get AI-enhanced descriptions via ContentForge. SEO-optimized from day one.",
      icon: "sparkles",
    },
  ],

  /* -- How It Works (4 steps) -- */
  howItWorks: [
    {
      step: 1,
      title: "Connect",
      description: "Link your supplier accounts and dropshipping store.",
    },
    {
      step: 2,
      title: "Discover",
      description: "Search catalogs or let TrendScout find winning products.",
    },
    {
      step: 3,
      title: "Import",
      description: "One-click import with images, variants, and pricing.",
    },
    {
      step: 4,
      title: "Sell",
      description: "Products go live in your store, optimized and ready.",
    },
  ],

  /* -- Pricing Tiers (4 tiers) -- */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "10 imports/month",
        "1 store",
        "AliExpress only",
        "Manual import",
      ],
      cta: "Start Free",
    },
    {
      tier: "starter",
      name: "Starter",
      price: 19,
      features: [
        "100 imports/month",
        "3 stores",
        "AliExpress + CJ",
        "Bulk import",
        "Basic price sync",
      ],
      cta: "Start Trial",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 49,
      popular: true,
      features: [
        "500 imports/month",
        "10 stores",
        "All suppliers",
        "Auto price sync",
        "TrendScout pipeline",
        "Priority support",
      ],
      cta: "Start Trial",
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
        "Dedicated manager",
        "SLA guarantee",
      ],
      cta: "Contact Sales",
    },
  ],

  /* -- Social Proof Stats -- */
  stats: [
    { value: "50K+", label: "Products Imported" },
    { value: "99.5%", label: "Import Success Rate" },
    { value: "3", label: "Supplier Platforms" },
    { value: "< 30s", label: "Average Import Time" },
  ],
};
