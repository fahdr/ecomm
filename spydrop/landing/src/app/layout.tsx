/**
 * Root layout for the service landing page.
 *
 * Responsible for:
 * 1. Loading Google Fonts specified in `landing.config.ts`
 * 2. Setting metadata (title, description, OpenGraph) from config
 * 3. Applying font CSS variables to the document
 * 4. Injecting service-specific color custom properties
 *
 * **For Developers:**
 *   - Fonts are loaded via `next/font/google` for automatic optimization.
 *   - CSS custom properties from landing.config.ts are injected via an inline
 *     `<style>` tag so they cascade to all components.
 *   - The dark class is applied to `<html>` by default for the SaaS aesthetic.
 *
 * **For QA Engineers:**
 *   - Verify that the page title and meta description match landing.config.ts.
 *   - Check that fonts load correctly (no FOUT/FOIT flash).
 *   - Ensure the OpenGraph image is accessible at the configured URL.
 *
 * **For Project Managers:**
 *   - All SEO metadata is automatically derived from the landing config.
 *   - No manual HTML editing needed to update branding.
 *
 * @param props - Standard Next.js layout props with children.
 * @returns The root HTML document wrapping all pages.
 */

import type { Metadata } from "next";
import { landingConfig } from "@/landing.config";
import "./globals.css";

/* ─── Metadata (derived from landing config) ─── */
export const metadata: Metadata = {
  title: `${landingConfig.name} — ${landingConfig.tagline}`,
  description: landingConfig.description,
  openGraph: {
    title: `${landingConfig.name} — ${landingConfig.tagline}`,
    description: landingConfig.description,
    type: "website",
    siteName: landingConfig.name,
  },
  twitter: {
    card: "summary_large_image",
    title: `${landingConfig.name} — ${landingConfig.tagline}`,
    description: landingConfig.description,
  },
};

/**
 * Root layout component that wraps every page.
 *
 * Injects:
 * - Google Fonts via `<link>` tags
 * - CSS custom properties for service colors
 * - Font family CSS variables
 *
 * @param props.children - The page content to render.
 * @returns The complete HTML document.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { colors, fonts } = landingConfig;

  /**
   * Build a Google Fonts URL for both heading and body fonts.
   * Handles the case where heading and body are the same font.
   */
  const uniqueFonts = [...new Set([fonts.heading, fonts.body])];
  const googleFontsUrl =
    "https://fonts.googleapis.com/css2?" +
    uniqueFonts
      .map(
        (font) =>
          `family=${font.replace(/ /g, "+")}:wght@300;400;500;600;700;800;900`
      )
      .join("&") +
    "&display=swap";

  return (
    <html lang="en" className="dark">
      <head>
        {/* Google Fonts — preconnect for performance */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link href={googleFontsUrl} rel="stylesheet" />

        {/* Inject service-specific CSS custom properties */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              :root {
                --landing-primary: ${colors.primary};
                --landing-primary-hex: ${colors.primaryHex};
                --landing-accent: ${colors.accent};
                --landing-accent-hex: ${colors.accentHex};
                --landing-bg: ${colors.background};
                --landing-bg-hex: ${colors.backgroundHex};
                --landing-glow: ${colors.primaryHex}4d;
                --landing-glow-strong: ${colors.primaryHex}80;
                --font-heading: "${fonts.heading}", system-ui, sans-serif;
                --font-body: "${fonts.body}", system-ui, sans-serif;
              }
            `,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
