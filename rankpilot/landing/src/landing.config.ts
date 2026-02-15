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
  name: "RankPilot",
  tagline: "Automated SEO Engine",
  description: "Automate your SEO with AI-generated blog posts, keyword tracking, sitemap generation, and schema markup. Climb search rankings on autopilot.",
  slug: "rankpilot",
  dashboardUrl: "http://localhost:3103",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.65 0.18 155)",
    primaryHex: "#10b981",
    accent: "oklch(0.72 0.15 140)",
    accentHex: "#34d399",
    background: "oklch(0.16 0.02 160)",
    backgroundHex: "#0a1f1a",
  },

  /* ── Typography ── */
  fonts: {
    heading: "General Sans",
    body: "Nunito Sans",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Climb Search Rankings on Autopilot",
    subheadline: "AI-powered SEO engine that writes blog posts, tracks keywords, generates sitemaps, and adds schema markup \u2014 all automatically.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "AI Blog Writer",
      description: "Generate SEO-optimized blog posts with AI that match your brand voice and target high-value keywords automatically.",
      icon: "zap",
    },
    {
      title: "Keyword Tracking",
      description: "Monitor your keyword positions across search engines in real time and get alerts when rankings change.",
      icon: "chart",
    },
    {
      title: "Schema Markup",
      description: "Automatically generate and inject JSON-LD structured data so search engines understand your content better.",
      icon: "shield",
    },
    {
      title: "SEO Audits",
      description: "Run comprehensive site audits that catch broken links, missing meta tags, slow pages, and indexing issues.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    { step: 1, title: "Add Your Sites", description: "Connect your domains with one-click verification and automatic sitemap import." },
    { step: 2, title: "AI Optimizes", description: "RankPilot generates blog posts, adds schema markup, and optimizes meta tags for every page." },
    { step: 3, title: "Track Rankings", description: "Monitor keyword positions, organic traffic, and site health with automated audits." },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "2 blog posts per month",
        "20 keywords tracked",
        "1 site",
        "Basic schema markup",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 29,
      popular: true,
      features: [
        "20 blog posts per month",
        "200 keywords tracked",
        "5 sites",
        "Advanced JSON-LD schema",
        "Content gap analysis",
        "Priority support",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 99,
      features: [
        "Unlimited blog posts",
        "Unlimited keywords tracked",
        "Unlimited sites",
        "Full API access",
        "Custom schema templates",
        "Dedicated account manager",
      ],
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "500K+", label: "Blog Posts Generated" },
    { value: "2M+", label: "Keywords Tracked" },
    { value: "99.9%", label: "Uptime" },
  ],
};
