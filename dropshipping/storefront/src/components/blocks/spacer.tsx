/**
 * Spacer block -- a vertical spacing element for the storefront homepage.
 *
 * Inserts configurable vertical whitespace between other blocks.  Store
 * owners use this to fine-tune the visual rhythm of their homepage layout.
 *
 * **For Developers:**
 *   This is a **server component** (no ``"use client"`` directive).
 *   The ``height`` config value maps to predefined Tailwind padding
 *   classes:  ``"sm"`` = ``py-4``, ``"md"`` = ``py-8``, ``"lg"`` =
 *   ``py-16``, ``"xl"`` = ``py-24``.  The rendered element is an empty
 *   ``<div>`` with ``aria-hidden="true"`` since it carries no content.
 *
 * **For QA Engineers:**
 *   - ``height`` defaults to "md" when not specified.
 *   - Valid values: "sm", "md", "lg", "xl".
 *   - Invalid height values fall back to "md".
 *   - The spacer renders as an empty, hidden element (invisible to
 *     assistive technology).
 *
 * **For Project Managers:**
 *   The spacer is a layout utility that gives store owners precise
 *   control over the spacing between homepage sections.  It contains
 *   no visible content -- just whitespace.
 *
 * **For End Users:**
 *   This element is invisible.  It controls the spacing between
 *   sections on the page.
 *
 * @module blocks/spacer
 */

/**
 * Props accepted by the {@link Spacer} component.
 */
interface SpacerProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``height`` ("sm" | "md" | "lg" | "xl") -- Spacer size (default "md").
   */
  config: Record<string, unknown>;
}

/**
 * Map a height size token to the corresponding Tailwind padding class.
 *
 * @param size - The height size token from config.
 * @returns A Tailwind ``py-*`` class string.
 */
function heightClass(size: string): string {
  const map: Record<string, string> = {
    sm: "py-4",
    md: "py-8",
    lg: "py-16",
    xl: "py-24",
  };
  return map[size] || "py-8";
}

/**
 * Render a vertical spacer element.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns An empty ``<div>`` with vertical padding.
 */
export function Spacer({ config }: SpacerProps) {
  const height = (config.height as string) || "md";

  return <div className={heightClass(height)} aria-hidden="true" />;
}
