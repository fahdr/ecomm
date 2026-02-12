/**
 * Service grid component — showcases all 8 SaaS products as interactive cards.
 *
 * Each card features:
 * - Service icon with brand color glow on hover
 * - Service name, tagline, and category badge
 * - Top 3 feature highlights
 * - CTA link to the individual service landing page
 *
 * Cards use IntersectionObserver for staggered scroll-reveal animations.
 *
 * **For Developers:**
 *   - Service data comes from `suite.config.ts`.
 *   - Icons are inline SVGs mapped by the `icon` key.
 *   - The hover glow effect uses a pseudo-element positioned absolutely.
 *   - Uses `reveal` + `reveal-delay-N` classes for scroll animation.
 *
 * **For QA Engineers:**
 *   - Verify all 8 cards render with correct brand colors.
 *   - Test card hover effects (glow, translateY).
 *   - Verify "Learn More" links point to correct service landing pages.
 *   - Test responsive layout: 1 col (mobile), 2 cols (tablet), 4 cols (desktop).
 *
 * @returns The service grid section JSX element.
 */
"use client";

import { useEffect, useRef } from "react";
import { services, type ServiceConfig } from "@/suite.config";

/** Maps icon keys to inline SVG paths. */
const iconPaths: Record<string, string> = {
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  pen: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
  chart: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  mail: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  eye: "M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z",
  share: "M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z",
  megaphone: "M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z",
  bot: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
};

/**
 * Renders an SVG icon for the given icon key.
 *
 * @param iconKey - The icon identifier from the service config.
 * @param color - The stroke color for the icon.
 * @returns An SVG element or null if icon key is not found.
 */
function ServiceIcon({ iconKey, color }: { iconKey: string; color: string }) {
  const path = iconPaths[iconKey];
  if (!path) return null;

  return (
    <svg
      className="h-6 w-6"
      fill="none"
      viewBox="0 0 24 24"
      stroke={color}
      strokeWidth={1.5}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

/**
 * Renders a single service card with brand colors, features, and CTA.
 *
 * @param service - The service configuration data.
 * @param index - The card's index for staggered animation delay.
 * @returns A service card JSX element.
 */
function ServiceCard({ service, index }: { service: ServiceConfig; index: number }) {
  return (
    <div
      className={`service-card reveal reveal-delay-${(index % 4) + 1} group relative overflow-hidden rounded-2xl border p-6`}
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface-raised)" }}
    >
      {/* Hover glow overlay */}
      <div
        className="service-glow absolute inset-0 rounded-2xl"
        style={{
          background: `radial-gradient(400px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${service.color}15, transparent 60%)`,
        }}
      />

      <div className="relative z-10">
        {/* Header: icon + badge */}
        <div className="mb-4 flex items-start justify-between">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${service.color}15` }}
          >
            <ServiceIcon iconKey={service.icon} color={service.color} />
          </div>
          <span
            className="rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider"
            style={{ backgroundColor: `${service.color}15`, color: service.color }}
          >
            {service.code}
          </span>
        </div>

        {/* Name + tagline */}
        <h3
          className="mb-1 text-lg font-bold"
          style={{ fontFamily: "var(--font-heading)", color: "var(--color-text)" }}
        >
          {service.name}
        </h3>
        <p
          className="mb-1 text-xs font-medium uppercase tracking-wider"
          style={{ color: service.color }}
        >
          {service.tagline}
        </p>
        <p
          className="mb-4 text-sm leading-relaxed"
          style={{ color: "var(--color-text-muted)" }}
        >
          {service.description}
        </p>

        {/* Highlights */}
        <ul className="mb-5 space-y-2">
          {service.highlights.map((h, i) => (
            <li key={i} className="flex items-start gap-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
              <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke={service.color} strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {h}
            </li>
          ))}
        </ul>

        {/* CTA */}
        <a
          href={service.landingUrl}
          className="inline-flex items-center gap-1.5 text-sm font-semibold transition-colors"
          style={{ color: service.color }}
        >
          Learn More
          <svg className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </a>
      </div>
    </div>
  );
}

export function ServiceGrid() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    /**
     * Sets up IntersectionObserver to trigger reveal animations
     * when service cards scroll into view.
     */
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    const reveals = sectionRef.current?.querySelectorAll(".reveal");
    reveals?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="products"
      className="relative py-24 sm:py-32"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="reveal mx-auto mb-16 max-w-2xl text-center">
          <span
            className="mb-4 inline-block rounded-full border px-4 py-1.5 text-xs font-medium"
            style={{ borderColor: "var(--color-border)", color: "var(--color-accent-violet)" }}
          >
            The Complete Suite
          </span>
          <h2
            className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            <span className="gradient-text">8 Tools.</span>{" "}
            <span style={{ color: "var(--color-text)" }}>One Platform.</span>
          </h2>
          <p className="text-lg" style={{ color: "var(--color-text-muted)" }}>
            Each tool is a standalone SaaS product — use them individually or
            unlock the full power of the suite with cross-service integrations.
          </p>
        </div>

        {/* Card grid */}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {services.map((svc, i) => (
            <ServiceCard key={svc.slug} service={svc} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
