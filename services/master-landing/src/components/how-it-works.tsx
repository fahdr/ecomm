/**
 * "How It Works" section — explains the 3-step journey from signup to automation.
 *
 * Uses a numbered timeline layout with connecting lines and staggered
 * scroll-reveal animations.
 *
 * **For Developers:**
 *   - Timeline connector uses a CSS gradient line between steps.
 *   - Each step card uses `.reveal` for scroll-triggered animation.
 *   - Step numbers use the brand gradient for visual consistency.
 *
 * **For QA Engineers:**
 *   - Verify all 3 steps render with correct numbering.
 *   - Check connecting lines are visible on desktop and hidden on mobile.
 *   - Test scroll reveal triggers at correct scroll position.
 *
 * @returns The how-it-works section JSX element.
 */
"use client";

import { useEffect, useRef } from "react";

/** The 3 steps explaining how the suite works. */
const steps = [
  {
    step: 1,
    title: "Choose Your Tools",
    description:
      "Pick the services that match your business needs — from product research to customer support. Start with one or unlock the full suite.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    ),
  },
  {
    step: 2,
    title: "Connect & Configure",
    description:
      "Link your store, set your preferences, and let the AI learn your brand voice. Each tool auto-configures based on your business profile.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
  },
  {
    step: 3,
    title: "Automate & Scale",
    description:
      "Watch your business grow on autopilot. AI handles research, content, SEO, marketing, and support while you focus on strategy.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
];

export function HowItWorks() {
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
    <section
      ref={sectionRef}
      id="how-it-works"
      className="relative py-24 sm:py-32"
    >
      {/* Background accent */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full opacity-6 blur-[120px]"
          style={{ background: "var(--color-accent-teal)" }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="reveal mx-auto mb-16 max-w-2xl text-center">
          <span
            className="mb-4 inline-block rounded-full border px-4 py-1.5 text-xs font-medium"
            style={{ borderColor: "var(--color-border)", color: "var(--color-accent-teal)" }}
          >
            Simple Setup
          </span>
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Up and Running in{" "}
            <span style={{ color: "var(--color-accent-teal)" }}>Minutes</span>
          </h2>
          <p className="text-lg" style={{ color: "var(--color-text-muted)" }}>
            No complex setup. No code required. Just choose, connect, and automate.
          </p>
        </div>

        {/* Timeline */}
        <div className="grid gap-8 lg:grid-cols-3">
          {steps.map((step, i) => (
            <div
              key={step.step}
              className={`reveal-scale reveal-delay-${i + 1} relative rounded-2xl border p-8`}
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-surface-raised)",
              }}
            >
              {/* Step number */}
              <div
                className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl text-white"
                style={{
                  background: `linear-gradient(135deg, var(--color-brand), var(--color-accent-violet))`,
                }}
              >
                <span className="text-xl font-bold">{step.step}</span>
              </div>

              {/* Content */}
              <h3
                className="mb-3 text-xl font-bold"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                {step.title}
              </h3>
              <p className="leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
                {step.description}
              </p>

              {/* Connector line (desktop only, not on last item) */}
              {i < steps.length - 1 && (
                <div
                  className="absolute -right-4 top-1/2 hidden h-px w-8 lg:block"
                  style={{
                    background: `linear-gradient(to right, var(--color-border), transparent)`,
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
