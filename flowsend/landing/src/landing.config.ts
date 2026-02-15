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
  name: "FlowSend",
  tagline: "Smart Email Marketing",
  description: "Build automated email flows that convert. Abandoned cart recovery, welcome sequences, win-back campaigns \u2014 all powered by AI with beautiful templates.",
  slug: "flowsend",
  dashboardUrl: "http://localhost:3104",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.65 0.20 25)",
    primaryHex: "#f43f5e",
    accent: "oklch(0.75 0.18 40)",
    accentHex: "#fb923c",
    background: "oklch(0.15 0.02 20)",
    backgroundHex: "#1f0f0f",
  },

  /* ── Typography ── */
  fonts: {
    heading: "Satoshi",
    body: "Source Sans 3",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Email Flows That Actually Convert",
    subheadline: "Visual flow builder with AI-powered copy, smart segmentation, and automated triggers for abandoned carts, welcome sequences, and win-back campaigns.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "Visual Flow Builder",
      description: "Design complex email automations with a drag-and-drop canvas. Set triggers, delays, conditions, and splits without writing code.",
      icon: "zap",
    },
    {
      title: "AI Email Copy",
      description: "Generate high-converting subject lines and email body content powered by AI that learns your brand voice over time.",
      icon: "chart",
    },
    {
      title: "Smart Segmentation",
      description: "Automatically segment contacts by behavior, purchase history, and engagement to send the right message at the right time.",
      icon: "shield",
    },
    {
      title: "A/B Testing",
      description: "Test subject lines, send times, and content variations to continuously optimize your open rates and conversions.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    { step: 1, title: "Build Your Flow", description: "Use the drag-and-drop builder to set up triggers, delays, and conditions for your email sequences." },
    { step: 2, title: "AI Writes Copy", description: "Let AI generate personalized subject lines and email content tailored to each contact segment." },
    { step: 3, title: "Analyze & Optimize", description: "Track opens, clicks, and conversions in real time. Run A/B tests to continuously improve results." },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "500 emails per month",
        "2 automated flows",
        "250 contacts",
        "Basic templates",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 39,
      popular: true,
      features: [
        "25,000 emails per month",
        "20 automated flows",
        "10,000 contacts",
        "A/B testing",
        "All templates",
        "Priority support",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 149,
      features: [
        "Unlimited emails",
        "Unlimited flows",
        "Unlimited contacts",
        "Full API access",
        "Dedicated IP",
        "Dedicated account manager",
      ],
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "50M+", label: "Emails Sent" },
    { value: "35%", label: "Avg Open Rate" },
    { value: "99.9%", label: "Deliverability" },
  ],
};
