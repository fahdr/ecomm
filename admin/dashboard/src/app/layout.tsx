/**
 * Root layout for the Super Admin Dashboard.
 *
 * Sets up the dark admin theme, loads Geist fonts (Sans for UI labels,
 * Mono for data/numbers), and applies global CSS variables.
 *
 * For Developers:
 *   This layout wraps all pages. The font CSS variables (--font-geist-sans
 *   and --font-geist-mono) are available globally via the <body> class.
 *
 * For QA Engineers:
 *   Verify that the page renders with dark background (#0a0e1a range)
 *   and that text is legible (light on dark).
 *
 * For Project Managers:
 *   This is the top-level layout that provides consistent styling
 *   across all admin dashboard pages.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

/** Geist Sans — used for UI labels, navigation, and body text. */
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

/** Geist Mono — used for data values, numbers, and code. */
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

/** Page metadata for the admin dashboard. */
export const metadata: Metadata = {
  title: "Super Admin | ecomm Platform",
  description:
    "Platform administration dashboard for monitoring services, LLM providers, costs, and system health.",
};

/**
 * Root layout component.
 *
 * @param children - The page content rendered inside the layout.
 * @returns The HTML document structure with fonts and theme applied.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
