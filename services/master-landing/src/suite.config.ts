/**
 * Master suite configuration — defines all 8 SaaS products in the dropshipping
 * automation suite.
 *
 * Each service entry contains its branding, description, key features, and
 * pricing summary. This single file drives the entire master landing page.
 *
 * **For Developers:**
 *   - Add new services by appending to the `services` array.
 *   - Colors use hex for simplicity (master page doesn't need OKLCH per-service).
 *   - The `slug` must match the service directory name under `services/`.
 *   - `landingUrl` and `dashboardUrl` are for local dev; override in production.
 *
 * **For Project Managers:**
 *   - This is the single source of truth for the suite overview page.
 *   - Reorder services by changing their position in the array.
 *
 * **For QA Engineers:**
 *   - Verify all 8 service cards render with correct colors and icons.
 *   - Test that CTA links point to the correct service landing pages.
 *
 * **For End Users:**
 *   - This page gives you an overview of every tool available in the suite.
 *   - Click any service card to learn more about that specific product.
 */

/** Configuration for a single service in the suite. */
export interface ServiceConfig {
  /** Internal slug (matches directory name). */
  slug: string;
  /** Display name shown on cards and headings. */
  name: string;
  /** Short tagline (5-10 words). */
  tagline: string;
  /** Longer description (1-2 sentences). */
  description: string;
  /** Feature code (A1-A8) for badge display. */
  code: string;
  /** Category label for filtering. */
  category: string;
  /** Primary brand color (hex). */
  color: string;
  /** Accent/secondary color (hex). */
  accent: string;
  /** Icon key used by the service card component. */
  icon: string;
  /** Top 3 features as short strings. */
  highlights: string[];
  /** Starting price in USD/month (0 = free tier available). */
  startingPrice: number;
  /** Landing page URL. */
  landingUrl: string;
  /** Dashboard URL. */
  dashboardUrl: string;
}

/** All 8 services in the automation suite. */
export const services: ServiceConfig[] = [
  {
    slug: "trendscout",
    name: "TrendScout",
    tagline: "AI-Powered Product Research",
    description:
      "Discover winning products before your competitors with AI-powered research across AliExpress, TikTok, Google Trends, and Reddit.",
    code: "A1",
    category: "Research",
    color: "#3b82f6",
    accent: "#38bdf8",
    icon: "search",
    highlights: [
      "Multi-source scanning (4+ platforms)",
      "AI scoring engine with demand signals",
      "Watchlist with automated alerts",
    ],
    startingPrice: 0,
    landingUrl: "/trendscout",
    dashboardUrl: "http://localhost:3101",
  },
  {
    slug: "contentforge",
    name: "ContentForge",
    tagline: "AI Content Generation",
    description:
      "Generate product descriptions, blog posts, ad copy, and social media content in seconds using fine-tuned AI models.",
    code: "A2",
    category: "Content",
    color: "#a855f7",
    accent: "#e879f9",
    icon: "pen",
    highlights: [
      "Product descriptions in 30+ languages",
      "SEO-optimized blog post generation",
      "AI image generation & editing",
    ],
    startingPrice: 0,
    landingUrl: "/contentforge",
    dashboardUrl: "http://localhost:3102",
  },
  {
    slug: "rankpilot",
    name: "RankPilot",
    tagline: "SEO Automation Engine",
    description:
      "Automate your SEO workflow — track keywords, run audits, generate blog posts, and manage structured data from one dashboard.",
    code: "A3",
    category: "SEO",
    color: "#22c55e",
    accent: "#4ade80",
    icon: "chart",
    highlights: [
      "Real-time keyword rank tracking",
      "Automated SEO audits & fixes",
      "AI blog post generation",
    ],
    startingPrice: 0,
    landingUrl: "/rankpilot",
    dashboardUrl: "http://localhost:3103",
  },
  {
    slug: "flowsend",
    name: "FlowSend",
    tagline: "Email Marketing Automation",
    description:
      "Build email campaigns, automation flows, and manage contacts with a visual editor. Send targeted emails that convert.",
    code: "A4",
    category: "Email",
    color: "#f59e0b",
    accent: "#fbbf24",
    icon: "mail",
    highlights: [
      "Visual automation flow builder",
      "Smart segmentation & targeting",
      "Real-time campaign analytics",
    ],
    startingPrice: 0,
    landingUrl: "/flowsend",
    dashboardUrl: "http://localhost:3104",
  },
  {
    slug: "spydrop",
    name: "SpyDrop",
    tagline: "Competitor Intelligence",
    description:
      "Monitor competitor stores, track their best-selling products, price changes, and new arrivals. Stay one step ahead.",
    code: "A5",
    category: "Intelligence",
    color: "#ef4444",
    accent: "#f87171",
    icon: "eye",
    highlights: [
      "Competitor store monitoring",
      "Price change alerts & history",
      "Best-seller detection",
    ],
    startingPrice: 0,
    landingUrl: "/spydrop",
    dashboardUrl: "http://localhost:3105",
  },
  {
    slug: "postpilot",
    name: "PostPilot",
    tagline: "Social Media Automation",
    description:
      "Schedule posts across Instagram, TikTok, Facebook, and Twitter. AI-generated captions and optimal posting times.",
    code: "A6",
    category: "Social",
    color: "#ec4899",
    accent: "#f472b6",
    icon: "share",
    highlights: [
      "Multi-platform scheduling",
      "AI caption generation",
      "Engagement analytics dashboard",
    ],
    startingPrice: 0,
    landingUrl: "/postpilot",
    dashboardUrl: "http://localhost:3106",
  },
  {
    slug: "adscale",
    name: "AdScale",
    tagline: "Ad Campaign Optimizer",
    description:
      "Manage and optimize ad campaigns across Google, Meta, and TikTok from one dashboard. AI-powered budget allocation and bidding.",
    code: "A7",
    category: "Advertising",
    color: "#06b6d4",
    accent: "#22d3ee",
    icon: "megaphone",
    highlights: [
      "Multi-platform ad management",
      "AI budget optimization",
      "Automated A/B testing",
    ],
    startingPrice: 0,
    landingUrl: "/adscale",
    dashboardUrl: "http://localhost:3107",
  },
  {
    slug: "shopchat",
    name: "ShopChat",
    tagline: "AI Customer Support",
    description:
      "Deploy AI chatbots trained on your products and policies. Handle customer inquiries 24/7 with human-like conversations.",
    code: "A8",
    category: "Support",
    color: "#14b8a6",
    accent: "#2dd4bf",
    icon: "bot",
    highlights: [
      "Custom AI chatbot training",
      "Knowledge base integration",
      "Live conversation handoff",
    ],
    startingPrice: 0,
    landingUrl: "/shopchat",
    dashboardUrl: "http://localhost:3108",
  },
];

/** Suite-level pricing tiers for the bundled offering. */
export const suitePricing = [
  {
    tier: "starter",
    name: "Starter Bundle",
    price: 49,
    description: "Pick any 3 services",
    features: [
      "Choose 3 services from the suite",
      "Free tier on each service",
      "Shared user account",
      "Community support",
      "Basic API access",
    ],
    cta: "Start Free Trial",
  },
  {
    tier: "growth",
    name: "Growth Bundle",
    price: 149,
    popular: true,
    description: "All 8 services, Pro tier",
    features: [
      "All 8 services included",
      "Pro tier on every service",
      "Unified dashboard",
      "Priority support",
      "Full API access",
      "Cross-service integrations",
    ],
    cta: "Start Growth Trial",
  },
  {
    tier: "enterprise",
    name: "Enterprise",
    price: -1,
    description: "Custom deployment",
    features: [
      "All services, unlimited usage",
      "Dedicated infrastructure",
      "Custom integrations",
      "SLA guarantee",
      "Dedicated account manager",
      "On-premise deployment option",
    ],
    cta: "Contact Sales",
  },
];

/** Suite-level social proof stats. */
export const suiteStats = [
  { value: "8", label: "AI-Powered Tools" },
  { value: "50K+", label: "Active Users" },
  { value: "2M+", label: "Tasks Automated" },
  { value: "99.9%", label: "Uptime" },
];
