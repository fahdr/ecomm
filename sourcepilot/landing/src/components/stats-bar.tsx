/**
 * Stats / social proof bar for SourcePilot.
 *
 * Displays 4 key metrics about SourcePilot's scale and reliability:
 * products imported, import success rate, supplier platforms, and
 * average import time.
 *
 * **For Developers:**
 *   - Count-up is driven by IntersectionObserver in the parent page.
 *   - The `.reveal` class controls visibility; `.is-visible` triggers the
 *     CSS animation defined in globals.css.
 *   - Numeric values are displayed as-is from config (pre-formatted strings).
 *   - The bar uses a 4-column grid on desktop, 2x2 on tablet, stacked on mobile.
 *   - Uses a subtle glass background to separate it from hero/features.
 *
 * **For QA Engineers:**
 *   - Verify all 4 numbers animate in when scrolled into view.
 *   - Check that the bar is centered and evenly spaced on all breakpoints.
 *   - Ensure no overflow on mobile with long stat labels.
 *   - Verify the "< 30s" value renders correctly with the angle bracket.
 *
 * **For End Users:**
 *   - These stats provide social proof about SourcePilot's adoption and speed.
 *
 * @returns The stats bar JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Renders the social proof statistics bar.
 *
 * Adapts from 1 column (mobile) to 2 columns (tablet) to 4 columns
 * (desktop) based on the number of stats in the config.
 *
 * @returns The stats bar section JSX element.
 */
export function StatsBar() {
  return (
    <section
      className="relative z-10 -mt-16 px-4 sm:px-6 lg:px-8"
      aria-label="Key metrics"
    >
      <div className="mx-auto max-w-5xl">
        <div
          className="glass reveal rounded-2xl px-6 py-8 sm:px-10 sm:py-10"
        >
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {landingConfig.stats.map((stat, index) => (
              <div
                key={stat.label}
                className={`reveal-delay-${index + 1} text-center`}
              >
                {/* Stat value -- large, bold, gradient text */}
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
