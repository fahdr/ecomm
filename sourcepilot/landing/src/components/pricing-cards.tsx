/**
 * Pricing section with 4-tier pricing cards for SourcePilot.
 *
 * Displays pricing tiers (Free, Starter, Pro, Enterprise) as cards with:
 * - Tier name and price
 * - "Popular" badge on the recommended Pro plan
 * - Feature checklist per tier
 * - CTA button per tier
 * - Hover effects (lift + glow on the popular card)
 *
 * **For Developers:**
 *   - All pricing data is config-driven from `landingConfig.pricing`.
 *   - Price of 0 shows "Free", price of -1 shows "Custom", positive shows "$X".
 *   - The `popular` flag adds visual emphasis: gradient border, glow shadow,
 *     and a "Most Popular" badge.
 *   - Cards use glassmorphism (`.glass`) with enhanced hover states.
 *   - The grid uses `lg:grid-cols-4` for the 4-tier layout.
 *
 * **For QA Engineers:**
 *   - Verify correct pricing display: $0 -> "Free", $19 -> "$19/mo",
 *     $49 -> "$49/mo", $199 -> "$199/mo".
 *   - Check that the "Most Popular" badge renders only on the Pro tier.
 *   - Hover effects: popular card has glow, others have subtle lift.
 *   - Mobile: cards should stack vertically with proper spacing.
 *   - Verify all CTA buttons link to the correct dashboard URL.
 *
 * **For Project Managers:**
 *   - Adding a new tier is a single object addition to landing.config.ts.
 *   - Feature lists per tier can be any length -- the card grows to fit.
 *
 * **For End Users:**
 *   - Compare plans from Free to Enterprise to find the right fit.
 *   - Click any CTA button to get started with that plan.
 *
 * @returns The pricing section JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Formats a price number for display.
 *
 * @param price - The price in USD. 0 = "Free", -1 = "Custom", positive = "$X".
 * @returns A formatted price string.
 */
function formatPrice(price: number): string {
  if (price === 0) return "Free";
  if (price < 0) return "Custom";
  return `$${price}`;
}

/**
 * Renders the pricing section with a responsive grid of tier cards.
 *
 * The grid adapts from 1 column (mobile) to 2 columns (tablet) to
 * 4 columns (desktop) for SourcePilot's 4-tier pricing model.
 *
 * @returns The pricing section JSX element.
 */
export function PricingCards() {
  return (
    <section
      id="pricing"
      className="relative py-24 sm:py-32"
      aria-label="Pricing"
    >
      {/* Background decoration */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full opacity-10 blur-[150px]"
          style={{ background: "var(--landing-primary-hex)" }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section heading */}
        <div className="reveal mb-16 text-center">
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl font-heading"
            style={{ color: "var(--landing-text)" }}
          >
            Simple, transparent{" "}
            <span className="gradient-text">pricing</span>
          </h2>
          <p
            className="mx-auto max-w-2xl text-lg"
            style={{ color: "var(--landing-text-muted)" }}
          >
            Start free with 10 imports per month and scale as your catalog grows.
            No hidden fees, no surprises.
          </p>
        </div>

        {/* Pricing cards grid -- 4 columns on desktop */}
        <div className="mx-auto grid max-w-6xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {landingConfig.pricing.map((tier, index) => (
            <div
              key={tier.tier}
              className={`reveal reveal-delay-${index + 1} relative rounded-2xl p-px transition-all duration-300 ${
                tier.popular
                  ? "scale-[1.02] lg:scale-105"
                  : "hover:scale-[1.02]"
              }`}
              style={
                tier.popular
                  ? {
                      background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))`,
                      boxShadow: `0 0 40px var(--landing-glow)`,
                    }
                  : undefined
              }
            >
              {/* Card inner (glass background) */}
              <div
                className={`relative h-full rounded-2xl p-6 lg:p-7 ${
                  tier.popular ? "" : "glass glass-hover"
                }`}
                style={
                  tier.popular
                    ? {
                        background: "var(--landing-bg-hex)",
                      }
                    : undefined
                }
              >
                {/* Popular badge */}
                {tier.popular && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-xs font-bold uppercase tracking-wider text-white"
                    style={{ background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))` }}
                  >
                    Most Popular
                  </div>
                )}

                {/* Tier name */}
                <h3
                  className="mb-2 text-lg font-semibold font-heading"
                  style={{ color: "var(--landing-text)" }}
                >
                  {tier.name}
                </h3>

                {/* Price */}
                <div className="mb-6 flex items-baseline gap-1">
                  <span
                    className="text-3xl font-extrabold tracking-tight font-heading lg:text-4xl"
                    style={{
                      color:
                        tier.popular
                          ? "var(--landing-primary-hex)"
                          : "var(--landing-text)",
                    }}
                  >
                    {formatPrice(tier.price)}
                  </span>
                  {tier.price > 0 && (
                    <span
                      className="text-sm"
                      style={{ color: "var(--landing-text-muted)" }}
                    >
                      /mo
                    </span>
                  )}
                </div>

                {/* Feature list */}
                <ul className="mb-8 space-y-3">
                  {tier.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-3 text-sm"
                    >
                      {/* Check icon */}
                      <svg
                        className="mt-0.5 h-4 w-4 shrink-0"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ color: "var(--landing-primary-hex)" }}
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      <span style={{ color: "var(--landing-text-muted)" }}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA button */}
                <a
                  href={landingConfig.dashboardUrl}
                  className={`block w-full rounded-xl py-3 text-center text-sm font-semibold transition-all hover:scale-[1.02] active:scale-95 ${
                    tier.popular
                      ? "text-white"
                      : ""
                  }`}
                  style={
                    tier.popular
                      ? {
                          background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))`,
                          boxShadow: `0 4px 20px var(--landing-glow)`,
                        }
                      : {
                          border: `1px solid var(--landing-border)`,
                          color: "var(--landing-text)",
                        }
                  }
                >
                  {tier.cta}
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
