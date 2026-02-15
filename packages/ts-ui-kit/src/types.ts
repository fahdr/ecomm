/**
 * Shared type definitions for the ecomm UI kit.
 *
 * These interfaces define the configuration shapes that services
 * pass to shared components (sidebar, top-bar, shell) to customize
 * their appearance and behavior.
 *
 * **For Developers:**
 *   - Import types: `import type { NavItem, ServiceConfig } from "@ecomm/ui-kit"`
 *   - Each service defines its own config implementing these interfaces.
 */

/**
 * A navigation item for the sidebar.
 *
 * For Developers:
 *   Define these in your service.config.ts and pass to the Sidebar component.
 *
 * For End Users:
 *   Each item appears as a clickable link in the sidebar navigation.
 */
export interface NavItem {
  /** Display label shown next to the icon. */
  label: string;
  /** Route path this item navigates to (e.g. "/billing"). */
  href: string;
  /** Lucide-react icon name (e.g. "LayoutDashboard", "CreditCard"). */
  icon: string;
}

/**
 * Billing plan tier for the plans page.
 *
 * For End Users:
 *   Shows the available subscription plans and their features.
 */
export interface PlanTier {
  /** Machine-readable tier ID (e.g. "free", "pro", "enterprise"). */
  tier: string;
  /** Display name (e.g. "Free", "Pro", "Enterprise"). */
  name: string;
  /** Monthly price string (e.g. "$0", "$29/mo"). */
  price: string;
  /** List of feature descriptions included in this plan. */
  features: string[];
}

/**
 * Service configuration for shared components.
 *
 * For Developers:
 *   Define this in your service's `service.config.ts` and pass to
 *   Shell, Sidebar, and TopBar components.
 */
export interface ServiceConfig {
  /** Service display name (e.g. "TrendScout"). */
  name: string;
  /** Short tagline (e.g. "AI Product Research"). */
  tagline: string;
  /** URL-safe slug (e.g. "trendscout"). Used for localStorage namespacing. */
  slug: string;
  /** Backend API base URL (e.g. "http://localhost:8101"). */
  apiUrl: string;
  /** Color theme. */
  colors: {
    /** Primary brand color in OKLCH (e.g. "oklch(0.65 0.25 240)"). */
    primary: string;
    /** Accent color in OKLCH. */
    accent: string;
    /** Primary color hex fallback (e.g. "#2563eb"). */
    primaryHex: string;
    /** Accent color hex fallback. */
    accentHex: string;
  };
  /** Font families. */
  fonts: {
    /** Heading font family (e.g. "Space Grotesk"). */
    heading: string;
    /** Body font family (e.g. "Inter"). */
    body: string;
  };
  /** Sidebar navigation items. */
  navigation: NavItem[];
  /** Billing plan tiers. */
  plans: PlanTier[];
}
