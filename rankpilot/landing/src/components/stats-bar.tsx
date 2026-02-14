/**
 * Stats / social proof bar.
 *
 * Displays 3-4 key metrics (e.g. "10K+ Active Users", "99.9% Uptime")
 * with a count-up animation that triggers on scroll into view.
 *
 * **For Developers:**
 *   - Count-up is driven by IntersectionObserver in the parent page.
 *   - The `.reveal` class controls visibility; `.is-visible` triggers the
 *     CSS animation defined in globals.css.
 *   - Numeric values are displayed as-is from config (pre-formatted strings).
 *   - The bar has a subtle glass background to separate it from hero/features.
 *
 * **For QA Engineers:**
 *   - Verify numbers animate in when scrolled into view.
 *   - Check that the bar is centered and evenly spaced on all breakpoints.
 *   - Ensure no overflow on mobile with long stat labels.
 *
 * **For End Users:**
 *   - These stats provide social proof about the product's adoption and reliability.
 *
 * @returns The stats bar JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

export function StatsBar() {
  return (
    <section
      className="relative z-10 -mt-16 px-4 sm:px-6 lg:px-8"
      aria-label="Key metrics"
    >
      <div className="mx-auto max-w-4xl">
        <div
          className="glass reveal rounded-2xl px-6 py-8 sm:px-10 sm:py-10"
        >
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {landingConfig.stats.map((stat, index) => (
              <div
                key={stat.label}
                className={`reveal-delay-${index + 1} text-center`}
              >
                {/* Stat value — large, bold, gradient text */}
                <div
                  className="gradient-text mb-1 text-3xl font-extrabold tracking-tight sm:text-4xl font-heading"
                >
                  {stat.value}
                </div>
                {/* Stat label */}
                <div
                  className="text-sm font-medium uppercase tracking-widest"
                  style={{ color: "var(--landing-text-muted)" }}
                >
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
