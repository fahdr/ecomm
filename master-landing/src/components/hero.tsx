/**
 * Hero section for the master suite landing page.
 *
 * Full-viewport hero with:
 * - Large gradient animated headline
 * - Suite value proposition
 * - Primary + secondary CTA buttons
 * - Abstract animated illustration with orbiting service icons
 * - Background glow effects and grid pattern
 *
 * **For Developers:**
 *   - All animations are CSS-only (defined in globals.css).
 *   - The orbiting dots represent the 8 services.
 *   - Colors reference CSS custom properties from the theme.
 *
 * **For QA Engineers:**
 *   - Verify hero fills the viewport on desktop (min-height: 100vh).
 *   - Check gradient text renders correctly across browsers.
 *   - Test CTA button links.
 *   - Verify reduced-motion disables all animations.
 *
 * @returns The hero section JSX element.
 */
"use client";

import { suiteStats } from "@/suite.config";

export function Hero() {
  return (
    <section
      className="relative flex min-h-screen items-center overflow-hidden"
      aria-label="Hero"
    >
      {/* ── Background Effects ── */}
      <div className="pointer-events-none absolute inset-0">
        {/* Top-left blue glow */}
        <div
          className="absolute left-[-15%] top-[-10%] h-[700px] w-[700px] rounded-full opacity-15 blur-[140px]"
          style={{ background: "var(--color-brand)" }}
        />
        {/* Bottom-right violet glow */}
        <div
          className="absolute bottom-[-20%] right-[-10%] h-[600px] w-[600px] rounded-full opacity-12 blur-[120px]"
          style={{ background: "var(--color-accent-violet)" }}
        />
        {/* Center teal glow */}
        <div
          className="absolute left-[40%] top-[30%] h-[400px] w-[400px] rounded-full opacity-8 blur-[100px]"
          style={{ background: "var(--color-accent-teal)" }}
        />
        {/* Grid overlay */}
        <div className="bg-grid-pattern absolute inset-0 opacity-20" />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-20 pt-28 sm:px-6 sm:pt-32 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          {/* ── Left Column: Copy + CTAs ── */}
          <div className="max-w-2xl">
            {/* Badge */}
            <div
              className="mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium opacity-0 animate-fade-in-up"
              style={{
                borderColor: "var(--color-border)",
                color: "var(--color-accent-teal)",
                animationDelay: "0ms",
                animationFillMode: "forwards",
              }}
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "var(--color-accent-teal)" }} />
              8 AI-powered tools — one platform
            </div>

            {/* Headline */}
            <h1
              className="mb-6 text-4xl font-black leading-[1.08] tracking-tight opacity-0 animate-fade-in-up sm:text-5xl lg:text-6xl xl:text-7xl"
              style={{ animationDelay: "100ms", animationFillMode: "forwards" }}
            >
              <span className="gradient-text">
                Automate Your Entire
              </span>
              <br />
              <span className="gradient-text-warm">
                Dropshipping Empire
              </span>
            </h1>

            {/* Subheadline */}
            <p
              className="mb-8 max-w-lg text-lg leading-relaxed opacity-0 animate-fade-in-up sm:text-xl"
              style={{
                color: "var(--color-text-muted)",
                animationDelay: "200ms",
                animationFillMode: "forwards",
              }}
            >
              From product research to customer support — 8 specialized AI tools
              that work together to scale your e-commerce business on autopilot.
            </p>

            {/* CTAs */}
            <div
              className="flex flex-col gap-4 opacity-0 animate-fade-in-up sm:flex-row"
              style={{ animationDelay: "300ms", animationFillMode: "forwards" }}
            >
              <a
                href="#pricing"
                className="group relative inline-flex items-center justify-center gap-2 rounded-xl px-8 py-4 text-base font-semibold text-white transition-all hover:scale-105 active:scale-95 animate-pulse-glow"
                style={{ backgroundColor: "var(--color-brand)" }}
              >
                Start Free Trial
                <svg className="h-4 w-4 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </a>
              <a
                href="#products"
                className="inline-flex items-center justify-center gap-2 rounded-xl border px-8 py-4 text-base font-semibold transition-all hover:scale-105 active:scale-95"
                style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
              >
                Explore Products
              </a>
            </div>

            {/* Stats bar */}
            <div
              className="mt-12 flex flex-wrap gap-8 opacity-0 animate-fade-in-up"
              style={{ animationDelay: "500ms", animationFillMode: "forwards" }}
            >
              {suiteStats.map((stat, i) => (
                <div key={i} className="flex flex-col">
                  <span
                    className="text-2xl font-bold tabular-nums"
                    style={{ color: "var(--color-brand-bright)" }}
                  >
                    {stat.value}
                  </span>
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {stat.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right Column: Animated Illustration ── */}
          <div className="relative hidden h-[520px] lg:block xl:h-[580px]" aria-hidden="true">
            {/* Central morphing orb */}
            <div
              className="absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 animate-morph opacity-25 blur-sm xl:h-64 xl:w-64"
              style={{ background: "linear-gradient(135deg, var(--color-brand), var(--color-accent-violet), var(--color-accent-teal))" }}
            />

            {/* Orbiting dots (representing 8 services) */}
            {[
              { color: "#3b82f6", delay: "0s", size: 12 },
              { color: "#a855f7", delay: "-1.5s", size: 10 },
              { color: "#22c55e", delay: "-3s", size: 11 },
              { color: "#f59e0b", delay: "-4.5s", size: 10 },
              { color: "#ef4444", delay: "-6s", size: 9 },
              { color: "#ec4899", delay: "-7.5s", size: 10 },
              { color: "#06b6d4", delay: "-9s", size: 11 },
              { color: "#14b8a6", delay: "-10.5s", size: 10 },
            ].map((dot, i) => (
              <div
                key={i}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
                style={{ animation: `orbit 12s linear ${dot.delay} infinite` }}
              >
                <div
                  className="rounded-full"
                  style={{
                    width: dot.size,
                    height: dot.size,
                    backgroundColor: dot.color,
                    boxShadow: `0 0 20px ${dot.color}80`,
                  }}
                />
              </div>
            ))}

            {/* Rotating grid pattern */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-spin-slow opacity-8">
              <svg width="400" height="400" viewBox="0 0 400 400" fill="none">
                <circle cx="200" cy="200" r="80" stroke="var(--color-brand)" strokeWidth="0.5" />
                <circle cx="200" cy="200" r="120" stroke="var(--color-accent-violet)" strokeWidth="0.5" />
                <circle cx="200" cy="200" r="160" stroke="var(--color-accent-teal)" strokeWidth="0.3" />
                <circle cx="200" cy="200" r="195" stroke="var(--color-brand)" strokeWidth="0.3" />
                <line x1="200" y1="5" x2="200" y2="395" stroke="var(--color-brand)" strokeWidth="0.3" />
                <line x1="5" y1="200" x2="395" y2="200" stroke="var(--color-brand)" strokeWidth="0.3" />
              </svg>
            </div>

            {/* Floating shapes */}
            <div
              className="absolute left-[12%] top-[18%] h-14 w-14 rounded-full animate-float opacity-50"
              style={{ background: "radial-gradient(circle, var(--color-brand), transparent)" }}
            />
            <div
              className="absolute right-[12%] top-[12%] h-20 w-20 rounded-full border animate-float-delayed opacity-30"
              style={{ borderColor: "var(--color-accent-violet)" }}
            />
            <div
              className="absolute bottom-[20%] left-[18%] h-8 w-8 rounded-full animate-float-slow opacity-40"
              style={{ backgroundColor: "var(--color-accent-teal)" }}
            />
          </div>
        </div>
      </div>

      {/* Bottom fade */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32"
        style={{ background: "linear-gradient(to bottom, transparent, var(--color-surface))" }}
      />
    </section>
  );
}
