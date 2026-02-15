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
  name: "PostPilot",
  tagline: "Social Media Automation",
  description: "Automate your social media across Instagram, Facebook, and TikTok. AI-generated captions, smart scheduling, and performance analytics in one dashboard.",
  slug: "postpilot",
  dashboardUrl: "http://localhost:3106",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.65 0.22 350)",
    primaryHex: "#ec4899",
    accent: "oklch(0.72 0.18 330)",
    accentHex: "#f472b6",
    background: "oklch(0.15 0.03 340)",
    backgroundHex: "#1f0a1a",
  },

  /* ── Typography ── */
  fonts: {
    heading: "Plus Jakarta Sans",
    body: "Quicksand",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Social Media on Autopilot",
    subheadline: "AI-powered social media manager that creates captions, schedules posts across Instagram, Facebook, and TikTok, and tracks performance \u2014 automatically.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "AI Captions",
      description: "Generate scroll-stopping captions and hashtags in seconds with AI trained on top-performing social content.",
      icon: "zap",
    },
    {
      title: "Multi-Platform Posting",
      description: "Publish to Instagram, Facebook, and TikTok from a single dashboard. One click, three platforms.",
      icon: "chart",
    },
    {
      title: "Smart Scheduling",
      description: "AI analyzes your audience to find the optimal posting times. Set it and forget it with auto-scheduling.",
      icon: "shield",
    },
    {
      title: "Analytics Dashboard",
      description: "Track engagement, reach, and growth across all platforms with unified performance analytics.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    {
      step: 1,
      title: "Connect Accounts",
      description: "Link your Instagram, Facebook, and TikTok accounts in seconds with secure OAuth integration.",
    },
    {
      step: 2,
      title: "AI Creates Content",
      description: "Our AI generates captions, suggests hashtags, and picks the optimal posting time for maximum engagement.",
    },
    {
      step: 3,
      title: "Schedule & Analyze",
      description: "Posts go out automatically on your schedule. Track engagement and optimize your strategy with real-time analytics.",
    },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "10 posts per month",
        "1 social platform",
        "5 AI captions per month",
        "Manual scheduling only",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      popular: true,
      features: [
        "200 posts per month",
        "All 3 platforms (Instagram, Facebook, TikTok)",
        "Unlimited AI captions",
        "Auto-scheduling with optimal timing",
        "Basic analytics",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 99,
      features: [
        "Unlimited posts",
        "All platforms + API access",
        "Unlimited AI captions & hashtags",
        "Auto-scheduling + full analytics",
        "Priority support",
      ],
      cta: "Go Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "10M+", label: "Posts Scheduled" },
    { value: "3", label: "Platforms" },
    { value: "2x", label: "Engagement Avg" },
  ],
};
