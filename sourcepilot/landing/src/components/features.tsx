/**
 * Features grid section for SourcePilot.
 *
 * Displays 6 feature cards in a 3x2 grid (desktop) or stacked (mobile),
 * each with an icon, title, and description. Cards use glassmorphism
 * styling and have hover lift + glow effects.
 *
 * **For Developers:**
 *   - Icons are mapped from the `icon` string in landing.config.ts to
 *     inline SVG components via `getFeatureIcon()`.
 *   - Add new icon keys by extending the switch statement.
 *   - Cards use `.glass` + `.glass-hover` classes from globals.css.
 *   - Scroll-triggered reveal uses `.reveal` + `.reveal-delay-N` classes.
 *   - The grid uses `sm:grid-cols-2 lg:grid-cols-3` for the 6-card layout.
 *
 * **For QA Engineers:**
 *   - Verify all 6 cards render with correct icon, title, and description.
 *   - Test hover effects: card should lift slightly and gain a glow border.
 *   - Check staggered reveal: cards should appear sequentially, not all at once.
 *   - Test with very long feature descriptions to ensure no overflow.
 *
 * **For Project Managers:**
 *   - Features are fully config-driven. Adding a 7th feature is a one-line
 *     addition to `landing.config.ts`. The grid auto-adjusts.
 *
 * **For End Users:**
 *   - This section highlights the key capabilities of SourcePilot:
 *     multi-supplier import, bulk operations, price intelligence,
 *     smart pricing, auto-import pipelines, and content enhancement.
 *
 * @returns The features grid section JSX element.
 */
"use client";

import { landingConfig } from "@/landing.config";

/**
 * Maps a feature icon key string to an inline SVG element.
 *
 * Each icon is designed to visually represent a SourcePilot capability.
 * Icons follow the Lucide icon style: 24x24 viewBox, 1.5px stroke,
 * round caps and joins.
 *
 * @param iconName - The icon key from landing.config.ts (e.g. "download", "upload").
 * @returns An SVG element for the icon, or a default diamond shape.
 */
function getFeatureIcon(iconName: string): React.ReactNode {
  /** Shared SVG props for consistent icon rendering. */
  const iconProps = {
    width: 28,
    height: 28,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (iconName) {
    case "download":
      return (
        <svg {...iconProps}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      );
    case "upload":
      return (
        <svg {...iconProps}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      );
    case "trending-up":
      return (
        <svg {...iconProps}>
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
          <polyline points="17 6 23 6 23 12" />
        </svg>
      );
    case "dollar-sign":
      return (
        <svg {...iconProps}>
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      );
    case "sparkles":
      return (
        <svg {...iconProps}>
          <path d="M12 3l1.912 5.813a2 2 0 0 0 1.275 1.275L21 12l-5.813 1.912a2 2 0 0 0-1.275 1.275L12 21l-1.912-5.813a2 2 0 0 0-1.275-1.275L3 12l5.813-1.912a2 2 0 0 0 1.275-1.275L12 3z" />
          <path d="M19 8l.7 2.1a1 1 0 0 0 .6.6L22.5 11.5l-2.1.7a1 1 0 0 0-.6.6L19 15l-.7-2.1a1 1 0 0 0-.6-.6L15.5 11.5l2.1-.7a1 1 0 0 0 .6-.6L19 8z" />
        </svg>
      );
    case "zap":
      return (
        <svg {...iconProps}>
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      );
    case "shield":
      return (
        <svg {...iconProps}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "chart":
      return (
        <svg {...iconProps}>
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
    case "globe":
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      );
    case "cpu":
      return (
        <svg {...iconProps}>
          <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
          <rect x="9" y="9" width="6" height="6" />
          <line x1="9" y1="1" x2="9" y2="4" />
          <line x1="15" y1="1" x2="15" y2="4" />
          <line x1="9" y1="20" x2="9" y2="23" />
          <line x1="15" y1="20" x2="15" y2="23" />
          <line x1="20" y1="9" x2="23" y2="9" />
          <line x1="20" y1="14" x2="23" y2="14" />
          <line x1="1" y1="9" x2="4" y2="9" />
          <line x1="1" y1="14" x2="4" y2="14" />
        </svg>
      );
    case "layers":
      return (
        <svg {...iconProps}>
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      );
    case "lock":
      return (
        <svg {...iconProps}>
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case "rocket":
      return (
        <svg {...iconProps}>
          <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
          <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
          <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 3 0 3 0" />
          <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-3 0-3" />
        </svg>
      );
    default:
      /* Default: diamond shape */
      return (
        <svg {...iconProps}>
          <rect
            x="4"
            y="4"
            width="16"
            height="16"
            rx="2"
            transform="rotate(45 12 12)"
            strokeWidth="1.5"
          />
        </svg>
      );
  }
}

/**
 * Renders the features section with a responsive grid of feature cards.
 *
 * The grid adapts from 1 column (mobile) to 2 columns (tablet) to
 * 3 columns (desktop) to accommodate the 6 SourcePilot features.
 *
 * @returns The features grid section JSX element.
 */
export function Features() {
  return (
    <section
      id="features"
      className="relative py-24 sm:py-32"
      aria-label="Features"
    >
      {/* Background decoration */}
      <div className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-20" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section heading */}
        <div className="reveal mb-16 text-center">
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl font-heading"
            style={{ color: "var(--landing-text)" }}
          >
            Everything you need to{" "}
            <span className="gradient-text">import smarter</span>
          </h2>
          <p
            className="mx-auto max-w-2xl text-lg"
            style={{ color: "var(--landing-text-muted)" }}
          >
            From one-click imports to automated price syncing, SourcePilot handles
            the heavy lifting so you can focus on growing your business.
          </p>
        </div>

        {/* Features grid — 3 columns on desktop for 6 cards */}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 lg:gap-8">
          {landingConfig.features.map((feature, index) => (
            <div
              key={feature.title}
              className={`reveal reveal-delay-${index + 1} glass glass-hover group cursor-default rounded-2xl p-8 transition-all duration-300`}
            >
              {/* Icon container */}
              <div
                className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl transition-colors duration-300"
                style={{
                  backgroundColor: "var(--landing-primary-hex)",
                  color: "white",
                  opacity: 0.9,
                }}
              >
                {getFeatureIcon(feature.icon)}
              </div>

              {/* Title */}
              <h3
                className="mb-3 text-xl font-semibold font-heading"
                style={{ color: "var(--landing-text)" }}
              >
                {feature.title}
              </h3>

              {/* Description */}
              <p
                className="leading-relaxed"
                style={{ color: "var(--landing-text-muted)" }}
              >
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
