/**
 * Image Banner block -- a full-width image section for the storefront
 * homepage, optionally wrapped in a link.
 *
 * Useful for promotional banners, seasonal campaigns, or brand imagery.
 *
 * **For Developers:**
 *   This is a **server component** (no ``"use client"`` directive).
 *   The ``image_url`` is rendered as an ``<img>`` tag inside a full-width
 *   container.  When ``link`` is provided, the image is wrapped in an
 *   ``<a>`` tag.  The ``height`` config value sets a max-height CSS style
 *   to keep the banner proportional.
 *
 * **For QA Engineers:**
 *   - Missing ``image_url`` renders nothing (no broken image placeholder).
 *   - ``alt`` defaults to "Banner" when not provided.
 *   - ``height`` defaults to "400px" and maps to ``max-height`` style.
 *   - If ``link`` is provided, the image is clickable.
 *   - If ``link`` is not provided, the image is decorative only.
 *   - Image uses ``object-cover`` to maintain aspect ratio.
 *
 * **For Project Managers:**
 *   Store owners use this block to showcase promotional banners or
 *   campaign imagery on their homepage.  The banner can optionally link
 *   to a product page, collection, or external URL.
 *
 * **For End Users:**
 *   This is a visual banner on the homepage.  It may link to a special
 *   offer or product page when clicked.
 *
 * @module blocks/image-banner
 */

/**
 * Props accepted by the {@link ImageBanner} component.
 */
interface ImageBannerProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``image_url`` (string) -- URL of the banner image.
   * - ``alt``       (string) -- Alt text for the image (default "Banner").
   * - ``link``      (string) -- Optional URL the banner links to.
   * - ``height``    (string) -- CSS max-height value (default "400px").
   */
  config: Record<string, unknown>;
}

/**
 * Render a full-width image banner with optional link wrapping.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A ``<section>`` element with the banner image, or null if no
 *          image URL is provided.
 */
export function ImageBanner({ config }: ImageBannerProps) {
  const imageUrl = (config.image_url as string) || "";
  const alt = (config.alt as string) || "Banner";
  const link = (config.link as string) || "";
  const height = (config.height as string) || "400px";

  // Don't render if there's no image
  if (!imageUrl) return null;

  /** The ``<img>`` element used in both linked and unlinked variants. */
  const imageElement = (
    <img
      src={imageUrl}
      alt={alt}
      className="w-full object-cover"
      style={{ maxHeight: height }}
      loading="lazy"
    />
  );

  return (
    <section className="w-full overflow-hidden">
      {link ? (
        <a
          href={link}
          className="block transition-opacity hover:opacity-95"
          target={link.startsWith("http") ? "_blank" : undefined}
          rel={link.startsWith("http") ? "noopener noreferrer" : undefined}
        >
          {imageElement}
        </a>
      ) : (
        imageElement
      )}
    </section>
  );
}
