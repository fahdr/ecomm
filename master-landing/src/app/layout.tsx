/**
 * Root layout for the master suite landing page.
 *
 * Loads Satoshi (heading) and General Sans (body) fonts from Fontsource CDN.
 * Sets up dark theme with global CSS variables.
 *
 * **For Developers:**
 *   - Fonts are loaded via Google Fonts link tags for simplicity in static export.
 *   - The `bg-noise` class adds a subtle texture overlay via CSS pseudo-element.
 *
 * **For QA Engineers:**
 *   - Verify fonts load correctly (check Network tab for font files).
 *   - Test that the page renders correctly without external fonts (fallback to system-ui).
 */
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DropShip Suite — 8 AI-Powered Tools for E-Commerce Automation",
  description:
    "The complete automation suite for dropshipping businesses. Product research, content generation, SEO, email marketing, competitor monitoring, social media, ad campaigns, and AI chatbots — all in one platform.",
};

/**
 * Root layout component wrapping all pages.
 *
 * @param children - Page content rendered inside the layout.
 * @returns The HTML document with fonts and global styles.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Satoshi + General Sans from Fontsource CDN */}
        <link
          rel="preconnect"
          href="https://api.fontshare.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://api.fontshare.com/v2/css?f[]=satoshi@700,900&f[]=general-sans@400,500,600&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-noise">{children}</body>
    </html>
  );
}
