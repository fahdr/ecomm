/**
 * Final CTA section — a full-width call-to-action with gradient background.
 *
 * Features a bold headline, supporting text, and a prominent action button.
 * Uses animated background effects for visual impact.
 *
 * **For Developers:**
 *   - Background uses CSS gradient + blur for the glow effect.
 *   - The CTA button uses `animate-pulse-glow` for attention.
 *
 * **For QA Engineers:**
 *   - Verify the section is visually distinct from surrounding content.
 *   - Test CTA button link and hover state.
 *
 * @returns The final CTA section JSX element.
 */
"use client";

import { useEffect, useRef } from "react";

export function CTA() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("is-visible");
        });
      },
      { threshold: 0.2 }
    );

    const reveals = sectionRef.current?.querySelectorAll(".reveal, .reveal-scale");
    reveals?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div
          className="reveal-scale relative overflow-hidden rounded-3xl border p-12 text-center sm:p-16 lg:p-20"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface-raised)",
          }}
        >
          {/* Background glows */}
          <div className="pointer-events-none absolute inset-0">
            <div
              className="absolute left-[-10%] top-[-20%] h-[400px] w-[400px] rounded-full opacity-15 blur-[100px]"
              style={{ background: "var(--color-brand)" }}
            />
            <div
              className="absolute bottom-[-20%] right-[-10%] h-[350px] w-[350px] rounded-full opacity-12 blur-[80px]"
              style={{ background: "var(--color-accent-violet)" }}
            />
          </div>

          <div className="relative z-10">
            <h2
              className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Ready to{" "}
              <span className="gradient-text">Automate</span>{" "}
              Your Business?
            </h2>
            <p
              className="mx-auto mb-8 max-w-2xl text-lg"
              style={{ color: "var(--color-text-muted)" }}
            >
              Join thousands of dropshippers who save 20+ hours per week with
              our AI-powered automation suite. Start free — no credit card required.
            </p>
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <a
                href="#pricing"
                className="inline-flex items-center gap-2 rounded-xl px-8 py-4 text-base font-semibold text-white transition-all hover:scale-105 active:scale-95 animate-pulse-glow"
                style={{ backgroundColor: "var(--color-brand)" }}
              >
                Start Your Free Trial
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </a>
              <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                14-day free trial on all plans
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
