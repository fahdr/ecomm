/**
 * Pricing section — displays suite-level bundle pricing tiers.
 *
 * Shows 3 tiers (Starter Bundle, Growth Bundle, Enterprise) with:
 * - Feature lists with checkmarks
 * - Highlighted "popular" tier
 * - Price display (free tier shows "$0", enterprise shows "Custom")
 * - CTA buttons
 *
 * **For Developers:**
 *   - Pricing data comes from `suite.config.ts` `suitePricing` array.
 *   - The "popular" tier gets a brand-colored border and glow.
 *   - Uses IntersectionObserver for scroll-reveal animations.
 *
 * **For QA Engineers:**
 *   - Verify all 3 tiers render with correct pricing.
 *   - Check that "Growth Bundle" has the "Most Popular" badge.
 *   - Test CTA button hover states.
 *   - Verify "Custom" displays for enterprise (price === -1).
 *
 * @returns The pricing section JSX element.
 */
"use client";

import { useEffect, useRef } from "react";
import { suitePricing } from "@/suite.config";

export function Pricing() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("is-visible");
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    const reveals = sectionRef.current?.querySelectorAll(".reveal, .reveal-scale");
    reveals?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} id="pricing" className="relative py-24 sm:py-32">
      {/* Background glow */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-8 blur-[140px]"
          style={{ background: "var(--color-accent-violet)" }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="reveal mx-auto mb-16 max-w-2xl text-center">
          <span
            className="mb-4 inline-block rounded-full border px-4 py-1.5 text-xs font-medium"
            style={{ borderColor: "var(--color-border)", color: "var(--color-accent-amber)" }}
          >
            Pricing
          </span>
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Simple,{" "}
            <span className="gradient-text-warm">Transparent</span>{" "}
            Pricing
          </h2>
          <p className="text-lg" style={{ color: "var(--color-text-muted)" }}>
            Start free with any individual tool. Bundle for massive savings.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid gap-8 lg:grid-cols-3">
          {suitePricing.map((tier, i) => {
            const isPopular = "popular" in tier && tier.popular;
            return (
              <div
                key={tier.tier}
                className={`reveal-scale reveal-delay-${i + 1} relative overflow-hidden rounded-2xl border p-8`}
                style={{
                  borderColor: isPopular ? "var(--color-brand)" : "var(--color-border)",
                  background: "var(--color-surface-raised)",
                  boxShadow: isPopular
                    ? "0 0 40px var(--glow-brand), 0 0 80px var(--glow-violet)"
                    : "none",
                }}
              >
                {/* Popular badge */}
                {isPopular && (
                  <div
                    className="absolute -right-12 top-6 rotate-45 px-14 py-1 text-[10px] font-bold uppercase tracking-wider text-white"
                    style={{ backgroundColor: "var(--color-brand)" }}
                  >
                    Most Popular
                  </div>
                )}

                {/* Tier name + description */}
                <h3
                  className="mb-1 text-xl font-bold"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {tier.name}
                </h3>
                <p className="mb-6 text-sm" style={{ color: "var(--color-text-muted)" }}>
                  {tier.description}
                </p>

                {/* Price */}
                <div className="mb-8">
                  {tier.price === -1 ? (
                    <span className="text-4xl font-bold" style={{ color: "var(--color-text)" }}>
                      Custom
                    </span>
                  ) : (
                    <div className="flex items-end gap-1">
                      <span className="text-4xl font-bold" style={{ color: "var(--color-text)" }}>
                        ${tier.price}
                      </span>
                      <span className="mb-1 text-sm" style={{ color: "var(--color-text-muted)" }}>
                        /month
                      </span>
                    </div>
                  )}
                </div>

                {/* Features */}
                <ul className="mb-8 space-y-3">
                  {tier.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2.5 text-sm" style={{ color: "var(--color-text-muted)" }}>
                      <svg
                        className="mt-0.5 h-4 w-4 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke={isPopular ? "var(--color-brand)" : "var(--color-accent-teal)"}
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <button
                  className="w-full rounded-xl py-3.5 text-sm font-semibold transition-all hover:scale-[1.02] active:scale-[0.98]"
                  style={{
                    backgroundColor: isPopular ? "var(--color-brand)" : "transparent",
                    color: isPopular ? "white" : "var(--color-text)",
                    border: isPopular ? "none" : "1px solid var(--color-border)",
                  }}
                >
                  {tier.cta}
                </button>
              </div>
            );
          })}
        </div>

        {/* Sub-note */}
        <p
          className="reveal mt-8 text-center text-sm"
          style={{ color: "var(--color-text-muted)" }}
        >
          All plans include a 14-day free trial. No credit card required.
          Each tool also available individually with its own free tier.
        </p>
      </div>
    </section>
  );
}
