/**
 * Root layout for the dashboard application.
 *
 * Sets up global fonts, styles, and the authentication provider that
 * wraps all pages. Every page in the dashboard has access to the
 * `useAuth()` hook via the `AuthProvider`.
 *
 * **For Developers:**
 *   The `AuthProvider` is a client component, but this layout remains
 *   a server component. The provider is imported and used as a wrapper
 *   around `{children}`.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/contexts/auth-context";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
