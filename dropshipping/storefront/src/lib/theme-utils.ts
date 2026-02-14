/**
 * Theme utility functions for dynamic font loading and CSS variable injection.
 *
 * **For Developers:**
 *   ``buildGoogleFontsUrl`` generates a Google Fonts CSS link for the theme's
 *   heading and body fonts. ``buildThemeCssVars`` converts the theme config
 *   into a CSS custom properties string for injection via ``<style>`` tag.
 *
 * **For QA Engineers:**
 *   - Only fonts from the curated library are used (validated by the backend).
 *   - CSS variables follow the ``--theme-*`` namespace to avoid collisions.
 *   - Dark mode variables are injected via ``.dark`` class selector.
 *
 * **For End Users:**
 *   These utilities ensure your store's theme (colors, fonts, and styles)
 *   loads correctly every time a customer visits your storefront.
 */

import type { StoreTheme } from "./types";

/**
 * Build a Google Fonts CSS import URL for the theme's fonts.
 *
 * Generates a single URL that loads both the heading and body fonts
 * with appropriate weights for optimal performance.
 *
 * @param theme - The store theme configuration.
 * @returns A Google Fonts CSS URL string, or null if no fonts are specified.
 */
export function buildGoogleFontsUrl(theme: StoreTheme): string | null {
  const fonts: string[] = [];

  const headingFont = theme.typography?.heading_font;
  const bodyFont = theme.typography?.body_font;
  const headingWeight = theme.typography?.heading_weight || "700";
  const bodyWeight = theme.typography?.body_weight || "400";

  if (headingFont) {
    const family = headingFont.replace(/\s+/g, "+");
    fonts.push(`family=${family}:wght@${headingWeight}`);
  }

  if (bodyFont && bodyFont !== headingFont) {
    const family = bodyFont.replace(/\s+/g, "+");
    fonts.push(`family=${family}:wght@${bodyWeight};700`);
  }

  if (fonts.length === 0) return null;

  return `https://fonts.googleapis.com/css2?${fonts.join("&")}&display=swap`;
}

/**
 * Convert a hex color string to an OKLCH-ish CSS value for theme consistency.
 *
 * For simplicity, we use hex values directly in CSS variables since the
 * backend stores colors as hex. The OKLCH conversion happens in the
 * dashboard's design system, not in the storefront.
 *
 * @param hex - A hex color string (e.g. "#0d9488").
 * @returns The hex string as-is (used directly in CSS vars).
 */
function colorValue(hex: string): string {
  return hex;
}

/**
 * Compute a contrasting text color for a given background hex color.
 *
 * Uses relative luminance to determine if black or white text
 * has better contrast against the background.
 *
 * @param hex - Background color as a hex string.
 * @returns "#ffffff" for dark backgrounds, "#1a1a1a" for light backgrounds.
 */
function contrastText(hex: string): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.substring(0, 2), 16) / 255;
  const g = parseInt(clean.substring(2, 4), 16) / 255;
  const b = parseInt(clean.substring(4, 6), 16) / 255;
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return luminance > 0.5 ? "#1a1a1a" : "#ffffff";
}

/**
 * Build inline CSS custom properties from a theme configuration.
 *
 * Generates a ``<style>`` tag content string with all theme variables
 * scoped to ``:root``. These variables drive the storefront's
 * dynamic appearance.
 *
 * @param theme - The store theme configuration.
 * @returns A CSS string ready to be injected into a ``<style>`` tag.
 */
export function buildThemeCssVars(theme: StoreTheme): string {
  const c = theme.colors || {};
  const t = theme.typography || {};
  const s = theme.styles || {};

  const headingFont = t.heading_font
    ? `"${t.heading_font}", sans-serif`
    : "sans-serif";
  const bodyFont = t.body_font
    ? `"${t.body_font}", sans-serif`
    : "sans-serif";

  const radiusMap: Record<string, string> = {
    none: "0",
    sm: "0.375rem",
    md: "0.5rem",
    lg: "0.75rem",
    xl: "1rem",
    full: "9999px",
  };
  const radius = radiusMap[s.border_radius] || radiusMap.md;

  // Typography weight/spacing/line-height tokens
  const headingWeight = t.heading_weight || "700";
  const bodyWeight = t.body_weight || "400";

  const letterSpacingMap: Record<string, string> = {
    tight: "-0.025em",
    normal: "0",
    wide: "0.05em",
  };
  const letterSpacing = letterSpacingMap[t.letter_spacing] || "0";

  const lineHeightMap: Record<string, string> = {
    compact: "1.3",
    normal: "1.6",
    relaxed: "1.8",
  };
  const lineHeight = lineHeightMap[t.line_height] || "1.6";

  return `
    :root {
      --theme-primary: ${colorValue(c.primary || "#0d9488")};
      --theme-primary-text: ${contrastText(c.primary || "#0d9488")};
      --theme-accent: ${colorValue(c.accent || "#d4a853")};
      --theme-accent-text: ${contrastText(c.accent || "#d4a853")};
      --theme-background: ${colorValue(c.background || "#fafaf8")};
      --theme-surface: ${colorValue(c.surface || c.card || "#ffffff")};
      --theme-text: ${colorValue(c.text || c.foreground || "#1a1a1a")};
      --theme-muted: ${colorValue(c.muted || c.muted_foreground || "#6b7280")};
      --theme-border: ${colorValue(c.border || "#e5e5e5")};
      --theme-font-heading: ${headingFont};
      --theme-font-body: ${bodyFont};
      --theme-heading-weight: ${headingWeight};
      --theme-body-weight: ${bodyWeight};
      --theme-letter-spacing: ${letterSpacing};
      --theme-line-height: ${lineHeight};
      --theme-radius: ${radius};
      --theme-card-style: ${s.card_style || "elevated"};
      --theme-button-style: ${s.button_style || "rounded"};
    }
  `.trim();
}

/**
 * Get the border radius class for buttons based on theme style.
 *
 * @param theme - The store theme configuration.
 * @returns A Tailwind-compatible border radius class.
 */
export function getButtonRadiusClass(theme: StoreTheme): string {
  const style = theme.styles?.button_style || "rounded";
  switch (style) {
    case "square":
      return "rounded-none";
    case "rounded":
      return "rounded-md";
    case "pill":
      return "rounded-full";
    default:
      return "rounded-md";
  }
}
