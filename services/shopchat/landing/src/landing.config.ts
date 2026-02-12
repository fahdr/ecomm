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
  name: "ShopChat",
  tagline: "AI Shopping Assistant",
  description: "Add an AI shopping assistant to your store. Answers questions, recommends products, and drives conversions — trained on your catalog and policies.",
  slug: "shopchat",
  dashboardUrl: "http://localhost:3108",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.55 0.20 275)",
    primaryHex: "#6366f1",
    accent: "oklch(0.70 0.18 290)",
    accentHex: "#818cf8",
    background: "oklch(0.14 0.03 280)",
    backgroundHex: "#13111f",
  },

  /* ── Typography ── */
  fonts: {
    heading: "Outfit",
    body: "Inter",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Your Store's Smartest Sales Assistant",
    subheadline: "AI-powered chat widget that answers customer questions, recommends products from your catalog, and converts browsers into buyers — 24/7.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "Product Recommendations",
      description: "Instantly suggest relevant products from your catalog based on customer questions, preferences, and browsing context.",
      icon: "zap",
    },
    {
      title: "Knowledge Base",
      description: "Train your bot on your full catalog, shipping policies, FAQs, and return rules so it answers accurately every time.",
      icon: "chart",
    },
    {
      title: "Customizable Widget",
      description: "Match your brand with custom colors, personality, welcome messages, and conversation flows — no code required.",
      icon: "shield",
    },
    {
      title: "Conversation Analytics",
      description: "Track conversation volume, resolution rates, product click-throughs, and revenue attributed to chat interactions.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    { step: 1, title: "Import Your Catalog", description: "Sync your products, policies, and FAQs. The AI learns your entire catalog so it can answer any customer question accurately." },
    { step: 2, title: "Customize Your Bot", description: "Set the personality, colors, and welcome message. Create guided flows for common questions like shipping, returns, and sizing." },
    { step: 3, title: "Embed & Convert", description: "Add a one-line snippet to your store. The widget deploys instantly and starts converting browsers into buyers around the clock." },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
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
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 19,
      popular: true,
      features: [
        "1,000 conversations/mo",
        "Full catalog sync",
        "Personality + flows",
        "Full analytics",
      ],
      cta: "Start Trial",
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
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "2M+", label: "Conversations" },
    { value: "15%", label: "Conv. Uplift" },
    { value: "24/7", label: "Availability" },
  ],
};
