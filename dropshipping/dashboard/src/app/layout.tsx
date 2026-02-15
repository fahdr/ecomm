/**
 * Root layout for the dashboard application.
 *
 * Sets up the design system fonts (Bricolage Grotesque for headings,
 * Instrument Sans for body, IBM Plex Mono for code), theme provider
 * for light/dark mode, toast notifications, and the authentication
 * provider that wraps all pages.
 *
 * **For Developers:**
 *   - Fonts are loaded via next/font/google and exposed as CSS variables
 *   - ThemeProvider from next-themes handles light/dark with class strategy
 *   - Toaster from sonner provides toast notifications globally
 *   - AuthProvider gives all pages access to useAuth() hook
 */

import type { Metadata } from "next";
import { Bricolage_Grotesque, Instrument_Sans, IBM_Plex_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { AuthProvider } from "@/contexts/auth-context";
import "./globals.css";

const headingFont = Bricolage_Grotesque({
  variable: "--font-heading",
  subsets: ["latin"],
  display: "swap",
});

const bodyFont = Instrument_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dropshipping Dashboard",
  description: "Manage your dropshipping stores, products, and orders.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${headingFont.variable} ${bodyFont.variable} ${monoFont.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange={false}
        >
          <AuthProvider>{children}</AuthProvider>
          <Toaster
            position="bottom-right"
            toastOptions={{
              className: "font-sans",
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
