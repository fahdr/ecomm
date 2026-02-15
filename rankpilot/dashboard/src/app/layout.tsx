/**
 * Root layout for the service dashboard.
 *
 * Loads Google Fonts (heading + body) specified in service.config.ts, wires up
 * the OKLCH color theme via CSS custom properties, and wraps all pages in
 * the html/body scaffold with font classes applied.
 *
 * **For Developers:**
 *   - Fonts are loaded via next/font/google and exposed as CSS variables
 *     (--font-heading, --font-body) consumed by globals.css.
 *   - The inline style on <html> sets --svc-primary / --svc-accent CSS vars
 *     so the theme can be changed per-service without modifying globals.css.
 *   - suppressHydrationWarning is required because the theme class is set
 *     client-side to avoid flash of wrong theme.
 *
 * **For Project Managers:**
 *   - All branding (title, description, colors) comes from service.config.ts.
 *   - Changing fonts or colors there automatically updates the entire UI.
 *
 * **For QA Engineers:**
 *   - Verify no FOUC (flash of unstyled content) on initial load.
 *   - Check that the correct fonts render (inspect computed font-family).
 *   - Test with slow network to ensure font swap: "swap" prevents invisible text.
 *
 * **For End Users:**
 *   - The dashboard automatically applies the service branding and fonts.
 *   - Dark/light mode is toggled from the sidebar.
 */

import type { Metadata } from "next";
import "./globals.css";
import { serviceConfig } from "@/service.config";

/**
 * Dynamic metadata derived from service configuration.
 * The title includes the service name; the description uses the tagline.
 */
export const metadata: Metadata = {
  title: `${serviceConfig.name} Dashboard`,
  description: serviceConfig.tagline,
};

/**
 * RootLayout wraps every page. It injects:
 *   1. Google Font CSS variables via className
 *   2. Service-specific OKLCH colors via inline CSS custom properties
 *   3. Dark mode class toggling via data attributes
 *
 * @param children - The page content rendered by Next.js routing.
 * @returns The complete HTML document shell.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      style={
        {
          "--svc-primary": serviceConfig.colors.primary,
          "--svc-primary-dark": serviceConfig.colors.primary,
          "--svc-accent": serviceConfig.colors.accent,
          "--svc-accent-dark": serviceConfig.colors.accent,
          "--font-heading": serviceConfig.fonts.heading,
          "--font-body": serviceConfig.fonts.body,
        } as React.CSSProperties
      }
    >
      <head>
        {/* Load heading font from Google Fonts */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href={`https://fonts.googleapis.com/css2?family=${encodeURIComponent(serviceConfig.fonts.heading)}:wght@400;500;600;700;800&family=${encodeURIComponent(serviceConfig.fonts.body)}:wght@300;400;500;600;700&display=swap`}
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
