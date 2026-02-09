/**
 * Custom Text block -- a simple, configurable text section for the
 * storefront homepage.
 *
 * Renders one or more paragraphs of plain text with configurable
 * alignment.  Store owners use this block to add announcements, brand
 * stories, or any freeform content to their homepage.
 *
 * **For Developers:**
 *   This is a **server component** (no ``"use client"`` directive).
 *   The ``content`` string is split on double newlines (``\n\n``) to
 *   create separate ``<p>`` elements.  The ``align`` config value maps
 *   directly to a ``text-*`` Tailwind utility.
 *
 * **For QA Engineers:**
 *   - Empty or missing ``content`` renders nothing (no empty section).
 *   - ``align`` accepts "left", "center", or "right"; defaults to "center".
 *   - Double newlines in ``content`` produce separate paragraphs.
 *   - Single newlines within the same paragraph are preserved as-is
 *     (normal HTML whitespace behavior).
 *
 * **For Project Managers:**
 *   This is a versatile block that gives store owners a way to add
 *   custom messaging to their homepage without needing code changes.
 *   The content and alignment are configured through the theme editor.
 *
 * **For End Users:**
 *   This section displays additional information from the store owner,
 *   such as announcements, brand story, or promotional text.
 *
 * @module blocks/custom-text
 */

/**
 * Props accepted by the {@link CustomText} component.
 */
interface CustomTextProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``content`` (string) -- The text content to render.
   * - ``align``   ("left" | "center" | "right") -- Text alignment (default "center").
   */
  config: Record<string, unknown>;
}

/**
 * Map an alignment config value to its Tailwind text-align class.
 *
 * @param align - The alignment value from config.
 * @returns A Tailwind ``text-*`` alignment class.
 */
function alignClass(align: string): string {
  const map: Record<string, string> = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
  };
  return map[align] || "text-center";
}

/**
 * Render a custom text section with configurable content and alignment.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A ``<section>`` element with paragraphs, or null if content is empty.
 */
export function CustomText({ config }: CustomTextProps) {
  const content = (config.content as string) || "";
  const align = (config.align as string) || "center";

  // Don't render an empty section
  if (!content.trim()) return null;

  // Split on double newlines to create separate paragraphs
  const paragraphs = content
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <section className={`mx-auto max-w-4xl px-6 py-16 ${alignClass(align)}`}>
      {paragraphs.map((paragraph, index) => (
        <p
          key={index}
          className="text-base leading-relaxed text-theme-muted mb-4 last:mb-0"
        >
          {paragraph}
        </p>
      ))}
    </section>
  );
}
