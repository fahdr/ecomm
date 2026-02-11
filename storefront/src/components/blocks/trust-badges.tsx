/**
 * Trust Badges block -- a row of icon-based trust signals like "Free Shipping",
 * "Secure Checkout", "Money-Back Guarantee", and "24/7 Support".
 *
 * **For Developers:**
 *   This is a **server component** (no state or effects needed).  Config:
 *   - ``badges``  (array)   -- Badge objects: { icon, title, description }.
 *   - ``columns`` (number)  -- Number of grid columns (default 4).
 *   Supported icon names: truck, shield, rotate-ccw, headphones, clock,
 *   award, lock, heart, star, zap, check-circle, package.
 *
 * **For QA Engineers:**
 *   - Empty ``badges`` array renders nothing.
 *   - Unknown icon names fall back to a generic check-circle icon.
 *   - Responsive: 2 columns on mobile, configured columns on large screens.
 *
 * **For End Users:**
 *   Trust indicators that show the store's commitment to quality service.
 *
 * @module blocks/trust-badges
 */

/** A single badge item from the block config. */
interface BadgeItem {
  icon: string;
  title: string;
  description?: string;
}

/** Props for the {@link TrustBadges} component. */
interface TrustBadgesProps {
  config: Record<string, unknown>;
}

/**
 * SVG icon paths keyed by icon name.
 * Uses Lucide-style 24x24 viewBox paths.
 */
const ICON_PATHS: Record<string, string> = {
  truck: "M1 3h15v13H1zM16 8h4l3 3v5h-7V8zM5.5 18.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM18.5 18.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  "rotate-ccw":
    "M1 4v6h6M3.51 15a9 9 0 1 0 2.13-9.36L1 10",
  headphones:
    "M3 18v-6a9 9 0 0 1 18 0v6M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2",
  award:
    "M12 15l-3.5 7 1-4.5L6 15h4L12 8l2 7h4l-3.5 2.5 1 4.5zM12 2a5 5 0 0 1 5 5 5 5 0 0 1-10 0 5 5 0 0 1 5-5z",
  lock: "M19 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2zM7 11V7a5 5 0 0 1 10 0v4",
  heart:
    "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
  star: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  "check-circle":
    "M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3",
  package:
    "M16.5 9.4l-9-5.19M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM3.27 6.96L12 12.01l8.73-5.05M12 22.08V12",
};

/** Fallback icon path (generic check-circle). */
const FALLBACK_ICON = ICON_PATHS["check-circle"];

/**
 * Map a column count to the corresponding Tailwind grid-cols class.
 * @param cols - Desired number of columns (2-6).
 * @returns A Tailwind ``lg:grid-cols-*`` class string.
 */
function gridColsClass(cols: number): string {
  const map: Record<number, string> = {
    2: "lg:grid-cols-2",
    3: "lg:grid-cols-3",
    4: "lg:grid-cols-4",
    5: "lg:grid-cols-5",
    6: "lg:grid-cols-6",
  };
  return map[cols] || "lg:grid-cols-4";
}

/**
 * Render a grid of trust badges with icons, titles, and descriptions.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with trust badge icons and labels.
 */
export function TrustBadges({ config }: TrustBadgesProps) {
  const rawBadges = Array.isArray(config.badges) ? config.badges : [];
  const badges: BadgeItem[] = rawBadges.filter(
    (b: unknown): b is BadgeItem =>
      typeof b === "object" && b !== null && "title" in b
  );
  const columns = typeof config.columns === "number" ? config.columns : 4;

  if (badges.length === 0) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <div className={`grid grid-cols-2 ${gridColsClass(columns)} gap-6`}>
        {badges.map((badge, i) => (
          <div
            key={i}
            className="flex flex-col items-center text-center p-6 rounded-xl border border-theme-border bg-theme-surface/50 hover:bg-theme-surface transition-colors"
          >
            {/* Icon */}
            <div className="w-12 h-12 rounded-full bg-theme-primary/10 flex items-center justify-center mb-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-theme-primary"
              >
                <path d={ICON_PATHS[badge.icon] || FALLBACK_ICON} />
              </svg>
            </div>

            {/* Title and description */}
            <h3 className="font-semibold text-sm mb-1">{badge.title}</h3>
            {badge.description && (
              <p className="text-xs text-theme-muted leading-relaxed">
                {badge.description}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
