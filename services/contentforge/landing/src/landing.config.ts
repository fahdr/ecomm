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
  name: "ContentForge",
  tagline: "AI Product Content Generator",
  description:
    "Transform raw product data into compelling, SEO-optimized listings in seconds. AI-powered titles, descriptions, bullet points, and image optimization.",
  slug: "contentforge",
  dashboardUrl: "http://localhost:3102",

  /* ── Colors (OKLCH + hex fallbacks) ── */
  colors: {
    primary: "oklch(0.60 0.22 300)",     // Violet Purple
    primaryHex: "#8b5cf6",               // Tailwind violet-500
    accent: "oklch(0.75 0.18 280)",      // Soft lavender accent
    accentHex: "#a78bfa",               // Tailwind violet-400
    background: "oklch(0.14 0.02 280)",  // Deep indigo background
    backgroundHex: "#1e1b2e",            // Custom dark purple
  },

  /* ── Typography ── */
  fonts: {
    heading: "Clash Display",
    body: "Satoshi",
  },

  /* ── Hero Section ── */
  hero: {
    headline: "Turn Raw Products Into Irresistible Listings",
    subheadline:
      "AI content engine that generates SEO-optimized titles, descriptions, bullet points, and meta tags from any product URL or data.",
    cta: "Get Started Free",
    secondaryCta: "View Pricing",
  },

  /* ── Features Grid (4 cards) ── */
  features: [
    {
      title: "AI Copywriting",
      description:
        "Generate compelling product titles, descriptions, and bullet points tailored to your brand voice and target audience with advanced language models.",
      icon: "zap",
    },
    {
      title: "Image Optimization",
      description:
        "Automatically enhance, resize, and optimize product images for web performance with AI-powered background removal and smart cropping.",
      icon: "shield",
    },
    {
      title: "Template System",
      description:
        "Choose from dozens of proven content templates for different platforms — Amazon, Shopify, eBay — or build your own custom templates.",
      icon: "chart",
    },
    {
      title: "Bulk Generation",
      description:
        "Import hundreds of products via CSV or URL and generate optimized content for your entire catalog in a single batch run.",
      icon: "globe",
    },
  ],

  /* ── How It Works (3 steps) ── */
  howItWorks: [
    {
      step: 1,
      title: "Import Product Data",
      description:
        "Paste a product URL, upload a CSV, or manually enter product details — ContentForge accepts any input format.",
    },
    {
      step: 2,
      title: "AI Generates Content",
      description:
        "Our AI engine produces SEO-optimized titles, rich descriptions, bullet points, and meta tags tuned to your chosen template and tone.",
    },
    {
      step: 3,
      title: "Review & Export",
      description:
        "Edit, approve, and push finished content directly to your store — or export as CSV for bulk upload to any platform.",
    },
  ],

  /* ── Pricing Tiers ── */
  pricing: [
    {
      tier: "free",
      name: "Free",
      price: 0,
      features: [
        "10 generations per month",
        "500 words per generation",
        "5 AI-optimized images",
        "Basic templates",
      ],
      cta: "Start Free",
    },
    {
      tier: "pro",
      name: "Pro",
      price: 19,
      popular: true,
      features: [
        "200 generations per month",
        "2,000 words per generation",
        "100 AI-optimized images",
        "All templates",
        "Bulk import & generation",
      ],
      cta: "Start Trial",
    },
    {
      tier: "enterprise",
      name: "Enterprise",
      price: 79,
      features: [
        "Unlimited generations",
        "Unlimited words per generation",
        "Unlimited images",
        "All templates + API access",
        "White-label output",
      ],
      cta: "Get Enterprise",
    },
  ],

  /* ── Social Proof Stats ── */
  stats: [
    { value: "1M+", label: "Listings Created" },
    { value: "8", label: "Content Types" },
    { value: "95%", label: "Time Saved" },
  ],
};
