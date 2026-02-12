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
  name: "AdScale",
  tagline: "AI Ad Campaign Manager",
  description: "Manage Google and Meta ad campaigns with AI. Auto-generate ad copy, optimize budgets, track ROAS, and scale winners — all from one dashboard.",
  slug: "adscale",
  dashboardUrl: "http://localhost:3107",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.72 0.18 80)",
    primaryHex: "#f59e0b",
    accent: "oklch(0.78 0.15 60)",
    accentHex: "#fbbf24",
    background: "oklch(0.14 0.02 80)",
    backgroundHex: "#1a1508",
  },

  /* ── Typography ── */
  fonts: {
    heading: "Inter Tight",
    body: "Inter",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Scale Your Ads With AI Precision",
    subheadline: "AI-powered campaign manager that creates ad copy, optimizes budgets across Google and Meta, tracks ROAS, and auto-scales your best performers.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "AI Ad Copy",
      description: "Generate high-converting headlines, descriptions, and creatives powered by AI — tailored to your audience and platform.",
      icon: "zap",
    },
    {
      title: "Budget Optimization",
      description: "Automatically allocate spend to top-performing campaigns and ad groups for maximum return on every dollar.",
      icon: "chart",
    },
    {
      title: "ROAS Tracking",
      description: "Real-time return on ad spend tracking across all platforms with unified dashboards and attribution insights.",
      icon: "shield",
    },
    {
      title: "Auto-Scaling Rules",
      description: "Set rules to automatically scale winners, pause underperformers, and adjust bids based on your ROAS targets.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    { step: 1, title: "Connect Ad Accounts", description: "Link your Google Ads and Meta Ads accounts in seconds. We sync campaigns, ad groups, and performance data automatically." },
    { step: 2, title: "AI Creates & Optimizes", description: "Our AI generates headlines, ad copy, and creative variations while continuously optimizing budgets and bids for peak performance." },
    { step: 3, title: "Scale Winners", description: "Auto-rules pause losing campaigns and scale profitable ones. Set ROAS targets and let the AI handle the rest." },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "2 campaigns",
        "1 platform",
        "5 AI copies/mo",
        "Manual optimization",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 49,
      popular: true,
      features: [
        "25 campaigns",
        "Google + Meta",
        "Unlimited AI copy",
        "Auto-optimization",
        "ROAS tracking",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 149,
      features: [
        "Unlimited campaigns",
        "All platforms + API",
        "Priority AI",
        "ROAS targets",
        "Dedicated support",
      ],
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "500K+", label: "Campaigns" },
    { value: "3.2x", label: "Avg ROAS" },
    { value: "$50M+", label: "Ad Spend Managed" },
  ],
};
