/**
 * Hero section for SourcePilot -- the primary above-the-fold content.
 *
 * This component makes the SourcePilot landing page visually distinctive. Features:
 * 1. Large animated headline with gradient text in warm orange/amber
 * 2. Descriptive subtitle about supplier import automation
 * 3. Primary ("Start Importing Free") + secondary ("View Pricing") CTA buttons
 * 4. Abstract CSS-only animated illustration representing product import flow:
 *    floating download arrows, supplier connection orbs, morphing shapes
 * 5. Full viewport height on desktop, responsive stacking on mobile
 *
 * **For Developers:**
 *   - All animations are CSS-only via classes defined in globals.css.
 *   - The abstract illustration uses absolutely positioned `<div>` elements
 *     with gradient backgrounds and CSS animations (float, morph, spin-slow).
 *   - The hero headline uses the `.gradient-text` class for animated
 *     gradient fill using the orange (#e05a33) and amber (#e8a838) palette.
 *   - The badge uses the service-specific "Import products in seconds" text.
 *
 * **For QA Engineers:**
 *   - Verify the hero fills the viewport on desktop (min-height: 100vh).
 *   - Test CTA buttons link to the correct dashboard URL.
 *   - Check that animations are smooth at 60fps (no jank).
 *   - Verify layout on narrow mobile screens (< 375px).
 *   - Test with `prefers-reduced-motion: reduce` -- no animations should play.
 *
 * **For End Users:**
 *   - The hero introduces SourcePilot and its core value proposition:
 *     importing products from AliExpress, CJDropship, and Spocket at scale.
 *   - Click "Start Importing Free" to sign up, or "View Pricing" to compare plans.
 *
 * @returns The hero section JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Renders the hero section with headline, subtitle, CTAs, and illustration.
 *
 * @returns The hero section JSX element.
 */
export function Hero() {
  return (
    <section
      className="relative flex min-h-screen items-center overflow-hidden"
      style={{ background: "var(--landing-bg-hex)" }}
      aria-label="Hero"
    >
      {/* -- Background Effects -- */}
      <div className="pointer-events-none absolute inset-0">
        {/* Radial gradient from top-left -- warm orange */}
        <div
          className="absolute left-[-20%] top-[-10%] h-[600px] w-[600px] rounded-full opacity-20 blur-[120px]"
          style={{ background: "var(--landing-primary-hex)" }}
        />
        {/* Radial gradient from bottom-right -- warm amber */}
        <div
          className="absolute bottom-[-15%] right-[-10%] h-[500px] w-[500px] rounded-full opacity-15 blur-[100px]"
          style={{ background: "var(--landing-accent-hex)" }}
        />
        {/* Subtle grid overlay */}
        <div className="bg-grid-pattern absolute inset-0 opacity-30" />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-20 pt-28 sm:px-6 sm:pt-32 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          {/* -- Left Column: Copy + CTAs -- */}
          <div className="max-w-2xl">
            {/* Chip / badge */}
            <div
              className="mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium animate-fade-in-up"
              style={{
                borderColor: "var(--landing-border)",
                color: "var(--landing-primary-hex)",
                animationDelay: "0ms",
              }}
            >
              <span
                className="h-1.5 w-1.5 rounded-full animate-pulse-glow"
                style={{ backgroundColor: "var(--landing-primary-hex)" }}
              />
              Import products in seconds
            </div>

            {/* Headline */}
            <h1
              className="mb-6 text-4xl font-extrabold leading-[1.1] tracking-tight opacity-0 animate-fade-in-up sm:text-5xl lg:text-6xl xl:text-7xl font-heading"
              style={{ animationDelay: "100ms", animationFillMode: "forwards" }}
            >
              <span className="gradient-text">
                {landingConfig.hero.headline}
              </span>
            </h1>

            {/* Subheadline */}
            <p
              className="mb-8 max-w-lg text-lg leading-relaxed opacity-0 animate-fade-in-up sm:text-xl"
              style={{
                color: "var(--landing-text-muted)",
                animationDelay: "200ms",
                animationFillMode: "forwards",
              }}
            >
              {landingConfig.hero.subheadline}
            </p>

            {/* CTA Buttons */}
            <div
              className="flex flex-col gap-4 opacity-0 animate-fade-in-up sm:flex-row"
              style={{ animationDelay: "300ms", animationFillMode: "forwards" }}
            >
              {/* Primary CTA */}
              <a
                href={landingConfig.dashboardUrl}
                className="group relative inline-flex items-center justify-center gap-2 rounded-xl px-8 py-4 text-base font-semibold text-white transition-all hover:scale-105 active:scale-95 animate-pulse-glow"
                style={{ backgroundColor: "var(--landing-primary-hex)" }}
              >
                {landingConfig.hero.cta}
                <svg
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
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

              {/* Secondary CTA */}
              <button
                onClick={() =>
                  document
                    .getElementById("pricing")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl border px-8 py-4 text-base font-semibold transition-all hover:scale-105 active:scale-95"
                style={{
                  borderColor: "var(--landing-border)",
                  color: "var(--landing-text)",
                }}
              >
                {landingConfig.hero.secondaryCta}
              </button>
            </div>

            {/* Supplier logos hint */}
            <div
              className="mt-8 flex items-center gap-3 opacity-0 animate-fade-in-up"
              style={{
                animationDelay: "500ms",
                animationFillMode: "forwards",
              }}
            >
              <span
                className="text-xs font-medium uppercase tracking-widest"
                style={{ color: "var(--landing-text-muted)", opacity: 0.6 }}
              >
                Supports
              </span>
              <div className="flex items-center gap-2">
                {["AliExpress", "CJDropship", "Spocket"].map((supplier) => (
                  <span
                    key={supplier}
                    className="rounded-md border px-2.5 py-1 text-xs font-medium"
                    style={{
                      borderColor: "var(--landing-border)",
                      color: "var(--landing-text-muted)",
                    }}
                  >
                    {supplier}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* -- Right Column: Abstract Animated Illustration -- */}
          <div
            className="relative hidden h-[500px] lg:block xl:h-[560px]"
            aria-hidden="true"
          >
            {/* Central orb -- morphing blob with warm gradients */}
            <div
              className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 animate-morph opacity-30 blur-sm xl:h-72 xl:w-72"
              style={{ background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))` }}
            />

            {/* Floating shape 1 -- small download arrow indicator */}
            <div
              className="absolute left-[15%] top-[20%] h-16 w-16 rounded-full animate-float opacity-60"
              style={{
                background: `radial-gradient(circle, var(--landing-primary-hex), transparent)`,
              }}
            />

            {/* Floating shape 2 -- medium ring (supplier connection) */}
            <div
              className="absolute right-[15%] top-[15%] h-24 w-24 rounded-full border-2 animate-float-delayed opacity-40"
              style={{ borderColor: "var(--landing-accent-hex)" }}
            />

            {/* Floating shape 3 -- accent dot */}
            <div
              className="absolute bottom-[25%] left-[20%] h-10 w-10 rounded-full animate-float-slow opacity-50"
              style={{ backgroundColor: "var(--landing-accent-hex)" }}
            />

            {/* Import flow arrows -- decorative downward arrow pattern */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-spin-slow opacity-10">
              <svg width="400" height="400" viewBox="0 0 400 400" fill="none">
                {/* Concentric circles representing supplier networks */}
                <circle
                  cx="200"
                  cy="200"
                  r="100"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                <circle
                  cx="200"
                  cy="200"
                  r="150"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                <circle
                  cx="200"
                  cy="200"
                  r="190"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                {/* Cross lines -- import flow directions */}
                <line
                  x1="200"
                  y1="10"
                  x2="200"
                  y2="390"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                <line
                  x1="10"
                  y1="200"
                  x2="390"
                  y2="200"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                {/* Diagonal lines */}
                <line
                  x1="58"
                  y1="58"
                  x2="342"
                  y2="342"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
                <line
                  x1="342"
                  y1="58"
                  x2="58"
                  y2="342"
                  stroke="var(--landing-primary-hex)"
                  strokeWidth="0.5"
                />
              </svg>
            </div>

            {/* Accent lines -- top-right decorative */}
            <div
              className="absolute right-[5%] top-[30%] h-32 w-px opacity-20 animate-fade-in-right"
              style={{
                background: `linear-gradient(to bottom, transparent, var(--landing-primary-hex), transparent)`,
                animationDelay: "500ms",
                animationFillMode: "forwards",
              }}
            />
            <div
              className="absolute right-[10%] top-[25%] h-px w-32 opacity-20 animate-fade-in-right"
              style={{
                background: `linear-gradient(to right, transparent, var(--landing-accent-hex), transparent)`,
                animationDelay: "600ms",
                animationFillMode: "forwards",
              }}
            />

            {/* Small floating dots */}
            <div
              className="absolute left-[40%] top-[10%] h-2 w-2 rounded-full animate-float opacity-60"
              style={{ backgroundColor: "var(--landing-primary-hex)" }}
            />
            <div
              className="absolute bottom-[15%] right-[30%] h-3 w-3 rounded-full animate-float-delayed opacity-40"
              style={{ backgroundColor: "var(--landing-accent-hex)" }}
            />
            <div
              className="absolute bottom-[40%] right-[8%] h-2 w-2 rounded-full animate-float-slow opacity-50"
              style={{ backgroundColor: "var(--landing-primary-hex)" }}
            />
          </div>
        </div>
      </div>

      {/* -- Bottom fade to next section -- */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32"
        style={{
          background: `linear-gradient(to bottom, transparent, var(--landing-bg-hex))`,
        }}
      />
    </section>
  );
}
