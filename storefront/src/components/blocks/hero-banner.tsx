/**
 * Hero Banner block -- a full-width introductory section for the storefront
 * homepage, typically placed at the very top of the page.
 *
 * Renders a large heading, optional subtitle, and a call-to-action button
 * against a configurable background (gradient, solid color, or image).
 *
 * **For Developers:**
 *   This is a **server component** (no ``"use client"`` directive).
 *   It reads its appearance from the ``config`` prop and applies CSS
 *   variables for theme-aware gradients.  Background types:
 *     - ``"gradient"`` (default): linear-gradient from ``--theme-primary``
 *       to ``--theme-accent``.
 *     - ``"solid"``: uses ``--theme-primary`` as a flat background.
 *     - ``"image"``: renders a background image from ``config.bg_image``
 *       with an overlay for text legibility.
 *
 * **For QA Engineers:**
 *   - Missing ``title`` defaults to "Welcome to our store".
 *   - Missing ``cta_text`` defaults to "Shop Now".
 *   - Missing ``cta_link`` defaults to "/products".
 *   - ``bg_type`` defaults to "gradient" when unspecified.
 *   - An image background shows a dark overlay so white text stays readable.
 *   - The section should be full-width regardless of parent constraints.
 *
 * **For Project Managers:**
 *   The hero banner is the first thing customers see when visiting a store.
 *   Store owners can customise the headline, sub-text, button label, link
 *   target, and background style through the theme editor in the dashboard.
 *
 * **For End Users:**
 *   This is the large banner at the top of the store homepage.  Click the
 *   button to start browsing products.
 *
 * @module blocks/hero-banner
 */

import Link from "next/link";

/**
 * Props accepted by the {@link HeroBanner} component.
 */
interface HeroBannerProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``title``     (string)  -- Heading text.
   * - ``subtitle``  (string)  -- Secondary text below the heading.
   * - ``cta_text``  (string)  -- Call-to-action button label.
   * - ``cta_link``  (string)  -- URL the CTA navigates to.
   * - ``bg_type``   ("gradient" | "solid" | "image") -- Background style.
   * - ``bg_image``  (string)  -- Image URL when bg_type is "image".
   */
  config: Record<string, unknown>;
}

/**
 * Render a full-width hero banner with heading, subtitle, and CTA button.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A ``<section>`` element with the hero content.
 */
export function HeroBanner({ config }: HeroBannerProps) {
  const title = (config.title as string) || "Welcome to our store";
  const subtitle = (config.subtitle as string) || "";
  const ctaText = (config.cta_text as string) || "Shop Now";
  const ctaLink = (config.cta_link as string) || "/products";
  const bgType = (config.bg_type as string) || "gradient";
  const bgImage = (config.bg_image as string) || "";

  /**
   * Determine inline styles and extra classNames based on the selected
   * background type.
   */
  const bgStyles: React.CSSProperties = {};
  let overlayNeeded = false;

  if (bgType === "image" && bgImage) {
    bgStyles.backgroundImage = `url(${bgImage})`;
    bgStyles.backgroundSize = "cover";
    bgStyles.backgroundPosition = "center";
    overlayNeeded = true;
  } else if (bgType === "solid") {
    bgStyles.backgroundColor = "var(--theme-primary)";
    bgStyles.color = "var(--theme-primary-text)";
  } else {
    // Default: gradient from primary to accent
    bgStyles.background =
      "linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-accent) 100%)";
    bgStyles.color = "var(--theme-primary-text)";
  }

  return (
    <section
      className="relative w-full overflow-hidden"
      style={bgStyles}
    >
      {/* Dark overlay for image backgrounds to ensure text legibility */}
      {overlayNeeded && (
        <div className="absolute inset-0 bg-black/50" aria-hidden="true" />
      )}

      <div className="relative mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:py-40 text-center">
        <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
          {title}
        </h1>

        {subtitle && (
          <p className="mt-6 mx-auto max-w-2xl text-lg sm:text-xl opacity-90 leading-relaxed">
            {subtitle}
          </p>
        )}

        <div className="mt-10">
          <Link
            href={ctaLink}
            className="inline-block btn-primary px-8 py-3.5 text-base font-semibold shadow-lg hover:shadow-xl transition-shadow"
          >
            {ctaText}
          </Link>
        </div>
      </div>
    </section>
  );
}
