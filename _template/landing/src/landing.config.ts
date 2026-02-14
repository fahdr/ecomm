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
  name: "{{SERVICE_DISPLAY_NAME}}",
  tagline: "{{SERVICE_TAGLINE}}",
  description: "{{SERVICE_DESCRIPTION}}",
  slug: "{{SERVICE_NAME}}",
  dashboardUrl: "http://localhost:{{DASHBOARD_PORT}}",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "{{PRIMARY_COLOR}}",
    primaryHex: "{{PRIMARY_HEX}}",
    accent: "{{ACCENT_COLOR}}",
    accentHex: "{{ACCENT_HEX}}",
    background: "{{BG_COLOR}}",
    backgroundHex: "{{BG_HEX}}",
  },

  /* ── Typography ── */
  fonts: {
    heading: "{{HEADING_FONT}}",
    body: "{{BODY_FONT}}",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "{{HERO_HEADLINE}}",
    subheadline: "{{HERO_SUBHEADLINE}}",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "Feature 1",
      description: "Description of the first key feature and its value proposition.",
      icon: "zap",
    },
    {
      title: "Feature 2",
      description: "Description of the second key feature and its value proposition.",
      icon: "shield",
    },
    {
      title: "Feature 3",
      description: "Description of the third key feature and its value proposition.",
      icon: "chart",
    },
    {
      title: "Feature 4",
      description: "Description of the fourth key feature and its value proposition.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    { step: 1, title: "Step 1", description: "Description of the first step in the process." },
    { step: 2, title: "Step 2", description: "Description of the second step in the process." },
    { step: 3, title: "Step 3", description: "Description of the third step in the process." },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "Up to 100 items",
        "Basic analytics",
        "Community support",
        "1 workspace",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      popular: true,
      features: [
        "Unlimited items",
        "Advanced analytics",
        "Priority support",
        "10 workspaces",
        "API access",
        "Custom integrations",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: -1,
      features: [
        "Everything in Pro",
        "Unlimited workspaces",
        "Dedicated support",
        "SLA guarantee",
        "Custom contracts",
        "On-premise option",
      ],
      cta: "Contact Sales",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "10K+", label: "Active Users" },
    { value: "50M+", label: "Items Analyzed" },
    { value: "99.9%", label: "Uptime" },
  ],
};
