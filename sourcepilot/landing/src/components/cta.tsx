/**
 * Final call-to-action section for SourcePilot.
 *
 * A visually striking section near the bottom of the page that encourages
 * visitors to start importing products. Features:
 * - Gradient background using the warm orange/amber palette
 * - Large headline asking "Ready to Scale Your Product Catalog?"
 * - Prominent CTA button with glow effect
 * - Animated background shapes for visual interest
 *
 * **For Developers:**
 *   - Background uses layered CSS gradients for depth.
 *   - Floating shapes reuse the same CSS animation classes as the hero.
 *   - The section is full-width with internal max-width constraint.
 *   - CTA links to the dashboard URL from landing.config.ts.
 *
 * **For QA Engineers:**
 *   - Verify the CTA button links to the correct dashboard URL.
 *   - Check contrast: white text on gradient background should be readable.
 *   - Test on mobile: ensure the section is not too tall on small screens.
 *   - Verify background shapes do not cause horizontal scroll on mobile.
 *
 * **For End Users:**
 *   - This is your final nudge to start importing products with SourcePilot.
 *
 * @returns The CTA section JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Renders the final call-to-action section.
 *
 * @returns The CTA section JSX element.
 */
export function CallToAction() {
  return (
    <section
      className="relative overflow-hidden py-24 sm:py-32"
      aria-label="Get started"
    >
      {/* Gradient background */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(135deg, var(--landing-primary-hex) 0%, var(--landing-bg-hex) 50%, var(--landing-accent-hex) 100%)`,
          opacity: 0.15,
        }}
      />

      {/* Animated background shapes */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        {/* Large blurred orb -- left */}
        <div
          className="absolute -left-20 top-1/2 h-72 w-72 -translate-y-1/2 rounded-full opacity-20 blur-[80px] animate-float"
          style={{ background: "var(--landing-primary-hex)" }}
        />
        {/* Medium blurred orb -- right */}
        <div
          className="absolute -right-16 bottom-0 h-56 w-56 rounded-full opacity-15 blur-[60px] animate-float-delayed"
          style={{ background: "var(--landing-accent-hex)" }}
        />
        {/* Small accent dots */}
        <div
          className="absolute left-[20%] top-[20%] h-3 w-3 rounded-full opacity-40 animate-float-slow"
          style={{ backgroundColor: "var(--landing-primary-hex)" }}
        />
        <div
          className="absolute right-[25%] top-[30%] h-2 w-2 rounded-full opacity-30 animate-float"
          style={{ backgroundColor: "var(--landing-accent-hex)" }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <div className="reveal">
          <h2
            className="mb-6 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl font-heading"
            style={{ color: "var(--landing-text)" }}
          >
            Ready to scale your product catalog?
          </h2>
          <p
            className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed"
            style={{ color: "var(--landing-text-muted)" }}
          >
            Join thousands of dropshippers who import products smarter, not harder.
            Connect your suppliers and start importing in minutes &mdash; no
            credit card required.
          </p>

          {/* CTA Button */}
          <a
            href={landingConfig.dashboardUrl}
            className="group inline-flex items-center gap-2 rounded-xl px-10 py-4 text-lg font-semibold text-white transition-all hover:scale-105 active:scale-95 animate-pulse-glow"
            style={{
              background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))`,
            }}
          >
            {landingConfig.hero.cta}
            <svg
              className="h-5 w-5 transition-transform group-hover:translate-x-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              />
            </svg>
          </a>

          {/* Trust line */}
          <p
            className="mt-6 text-sm"
            style={{ color: "var(--landing-text-muted)", opacity: 0.7 }}
          >
            Free plan available &bull; No credit card required &bull; Cancel anytime
          </p>
        </div>
      </div>
    </section>
  );
}
