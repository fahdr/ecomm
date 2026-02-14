/**
 * "How it works" section for SourcePilot -- a 4-step process visualization.
 *
 * Displays numbered steps (Connect, Discover, Import, Sell) with titles and
 * descriptions, connected by decorative lines/arrows. Each step reveals
 * sequentially on scroll.
 *
 * **For Developers:**
 *   - Steps are config-driven from `landingConfig.howItWorks`.
 *   - The connecting line between steps uses a CSS gradient that fades
 *     from the primary (orange) to accent (amber) color.
 *   - On mobile, steps stack vertically with a left-aligned connecting line.
 *   - On desktop, steps are arranged horizontally in a 4-column grid.
 *   - Each step has a numbered circle with a gradient background.
 *
 * **For QA Engineers:**
 *   - Verify all 4 steps render in order with correct numbers.
 *   - Check the connecting line/arrow between steps is visible on desktop.
 *   - On mobile, verify vertical stacking with left-side connector.
 *   - Test scroll reveal: steps should appear 1 -> 2 -> 3 -> 4 with delays.
 *
 * **For Project Managers:**
 *   - Adding or removing steps only requires editing `landing.config.ts`.
 *   - The layout automatically adjusts for 2, 3, or 4 steps.
 *
 * **For End Users:**
 *   - This section explains the simple 4-step process to get started
 *     importing products with SourcePilot.
 *
 * @returns The "How it works" section JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Renders the "How it works" section with numbered steps.
 *
 * Uses a 4-column grid on desktop (`lg:grid-cols-4`) to accommodate
 * SourcePilot's 4-step workflow: Connect, Discover, Import, Sell.
 *
 * @returns The "How it works" section JSX element.
 */
export function HowItWorks() {
  const steps = landingConfig.howItWorks;

  return (
    <section
      id="how-it-works"
      className="relative py-24 sm:py-32"
      aria-label="How it works"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section heading */}
        <div className="reveal mb-16 text-center">
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl font-heading"
            style={{ color: "var(--landing-text)" }}
          >
            Four steps to{" "}
            <span className="gradient-text">import success</span>
          </h2>
          <p
            className="mx-auto max-w-2xl text-lg"
            style={{ color: "var(--landing-text-muted)" }}
          >
            From connecting your supplier accounts to selling optimized products,
            SourcePilot streamlines the entire import workflow.
          </p>
        </div>

        {/* Steps grid -- horizontal on desktop, vertical on mobile */}
        <div className="relative">
          {/* Connecting line (desktop only) */}
          <div
            className="absolute left-0 right-0 top-16 hidden h-px lg:block"
            style={{
              background: `linear-gradient(to right, transparent, var(--landing-primary-hex), var(--landing-accent-hex), transparent)`,
              opacity: 0.3,
            }}
          />

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
            {steps.map((step, index) => (
              <div
                key={step.step}
                className={`reveal reveal-delay-${index + 1} relative`}
              >
                {/* Step card */}
                <div className="relative flex flex-col items-center text-center lg:items-center">
                  {/* Step number circle */}
                  <div
                    className="relative z-10 mb-6 flex h-14 w-14 items-center justify-center rounded-full text-lg font-bold text-white shadow-lg"
                    style={{
                      background: `linear-gradient(135deg, var(--landing-primary-hex), var(--landing-accent-hex))`,
                      boxShadow: `0 4px 20px var(--landing-glow)`,
                    }}
                  >
                    {step.step}
                  </div>

                  {/* Mobile connecting line (between steps, not after last) */}
                  {index < steps.length - 1 && (
                    <div
                      className="absolute left-1/2 top-14 h-8 w-px -translate-x-1/2 sm:hidden"
                      style={{
                        background: `linear-gradient(to bottom, var(--landing-primary-hex), transparent)`,
                        opacity: 0.3,
                      }}
                    />
                  )}

                  {/* Step content */}
                  <h3
                    className="mb-3 text-xl font-semibold font-heading"
                    style={{ color: "var(--landing-text)" }}
                  >
                    {step.title}
                  </h3>
                  <p
                    className="max-w-xs leading-relaxed"
                    style={{ color: "var(--landing-text-muted)" }}
                  >
                    {step.description}
                  </p>

                  {/* Arrow to next step (desktop only, not on last step) */}
                  {index < steps.length - 1 && (
                    <div
                      className="absolute -right-4 top-16 hidden -translate-y-1/2 lg:block"
                      style={{ color: "var(--landing-primary-hex)", opacity: 0.4 }}
                    >
                      <svg
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
