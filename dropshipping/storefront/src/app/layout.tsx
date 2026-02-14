/**
 * Root layout for the storefront app with dynamic theme loading.
 *
 * Resolves the store slug, fetches store data and the active theme from
 * the backend API, then injects dynamic CSS variables and Google Fonts
 * for the theme's visual configuration.
 *
 * **For Developers:**
 *   This is a server component. Theme data is fetched at request time
 *   and injected as a ``<style>`` tag with CSS custom properties.
 *   Google Fonts are loaded via a ``<link>`` tag in ``<head>``.
 *   The ``ThemeProvider`` from ``next-themes`` enables light/dark toggle.
 *
 * **For QA Engineers:**
 *   - Theme colors should match the active theme set in the dashboard.
 *   - Fonts should load from Google Fonts based on theme typography config.
 *   - Dark mode toggle should persist via localStorage.
 *   - If no theme is found, Frosted fallback colors apply from globals.css.
 *
 * **For End Users:**
 *   Your store's appearance (colors, fonts, and layout) is determined
 *   by the active theme you've selected in the dashboard.
 */

import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import Link from "next/link";
import type { Store, StoreTheme } from "@/lib/types";
import { StoreProvider } from "@/contexts/store-context";
import { CartProvider } from "@/contexts/cart-context";
import { CartBadge } from "@/components/cart-badge";
import { HeaderSearch } from "@/components/header-search";
import { ThemeToggle } from "@/components/theme-toggle";
import { AccountLink } from "@/components/account-link";
import { MobileMenu } from "@/components/mobile-menu";
import { buildGoogleFontsUrl, buildThemeCssVars } from "@/lib/theme-utils";
import { ThemeProvider } from "next-themes";
import { CustomerAuthProvider } from "@/contexts/auth-context";

/**
 * Generate dynamic metadata based on the resolved store.
 *
 * @returns Metadata object with store name as title and description.
 */
export async function generateMetadata(): Promise<Metadata> {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  if (!slug) {
    return {
      title: "Store Not Found",
      description: "The requested store could not be found.",
    };
  }

  const store = await fetchStore(slug);

  if (!store) {
    return {
      title: "Store Not Found",
      description: "The requested store could not be found.",
    };
  }

  return {
    title: {
      default: store.name,
      template: `%s | ${store.name}`,
    },
    description: store.description || `Shop at ${store.name} — ${store.niche}`,
    openGraph: {
      title: store.name,
      description: store.description || `Shop at ${store.name} — ${store.niche}`,
      type: "website",
    },
  };
}

/**
 * Root layout component with dynamic theme injection.
 *
 * Fetches the store and its active theme, injects CSS variables and
 * Google Fonts, and wraps all pages with store context and cart provider.
 *
 * @param props - Layout props containing children to render.
 * @param props.children - The page content to render inside the layout.
 * @returns The complete HTML document with theme-aware chrome.
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  let store: Store | null = null;
  let theme: StoreTheme | null = null;

  if (slug) {
    store = await fetchStore(slug);
    if (store) {
      const { data } = await api.get<StoreTheme>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/theme`
      );
      theme = data;
    }
  }

  const fontsUrl = theme ? buildGoogleFontsUrl(theme) : null;
  const themeCss = theme ? buildThemeCssVars(theme) : "";

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {fontsUrl && (
          <>
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link
              rel="preconnect"
              href="https://fonts.gstatic.com"
              crossOrigin="anonymous"
            />
            <link rel="stylesheet" href={fontsUrl} />
          </>
        )}
        {theme?.favicon_url && (
          <link rel="icon" href={theme.favicon_url} />
        )}
        {themeCss && <style dangerouslySetInnerHTML={{ __html: themeCss }} />}
        {theme?.custom_css && (
          <style dangerouslySetInnerHTML={{ __html: theme.custom_css }} />
        )}
      </head>
      <body className="antialiased min-h-screen flex flex-col">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          <StoreProvider store={store}>
            <CartProvider>
              <CustomerAuthProvider>
                {store && <StoreHeader store={store} theme={theme} />}
                <main className="flex-1">{children}</main>
                {store && <StoreFooter store={store} />}
              </CustomerAuthProvider>
            </CartProvider>
          </StoreProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

/**
 * Store header component with theme-aware styling.
 *
 * Displays the store logo or name, navigation links, search, cart,
 * and dark mode toggle. Colors and fonts adapt to the active theme.
 *
 * @param props - Component props.
 * @param props.store - The resolved store data.
 * @param props.theme - The active theme config (may be null).
 * @returns A header element with theme-driven branding.
 */
function StoreHeader({
  store,
  theme,
}: {
  store: Store;
  theme: StoreTheme | null;
}) {
  return (
    <header className="border-b border-theme bg-theme-surface/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-4 sm:gap-6">
            <MobileMenu storeName={store.name} />
            <Link href="/" className="flex items-center gap-3">
              {theme?.logo_url ? (
                <img
                  src={theme.logo_url}
                  alt={store.name}
                  className="h-8 w-auto"
                />
              ) : (
                <h1 className="text-xl font-heading font-bold tracking-tight">
                  {store.name}
                </h1>
              )}
            </Link>
            <nav className="hidden sm:flex items-center gap-4">
              <Link
                href="/products"
                className="text-sm text-theme-muted hover:text-theme-primary transition-colors"
              >
                Products
              </Link>
              <Link
                href="/categories"
                className="text-sm text-theme-muted hover:text-theme-primary transition-colors"
              >
                Categories
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <HeaderSearch />
            <ThemeToggle />
            <AccountLink />
            <CartBadge />
          </div>
        </div>
      </div>
    </header>
  );
}

/**
 * Store footer component with multi-column navigation and theme-aware styling.
 *
 * Four-column layout on desktop, two on tablet, stacked on mobile.
 * Includes shop links, customer service pages, account links, and about pages.
 *
 * @param props - Component props.
 * @param props.store - The resolved store data.
 * @returns A footer element with navigation columns and copyright.
 */
function StoreFooter({ store }: { store: Store }) {
  return (
    <footer className="border-t border-theme bg-theme-surface">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Shop */}
          <div>
            <h3 className="text-sm font-heading font-semibold mb-3">Shop</h3>
            <ul className="space-y-2 text-sm text-theme-muted">
              <li>
                <Link href="/products" className="hover:text-theme-primary transition-colors">
                  All Products
                </Link>
              </li>
              <li>
                <Link href="/categories" className="hover:text-theme-primary transition-colors">
                  Categories
                </Link>
              </li>
              <li>
                <Link href="/search" className="hover:text-theme-primary transition-colors">
                  Search
                </Link>
              </li>
            </ul>
          </div>

          {/* Customer Service */}
          <div>
            <h3 className="text-sm font-heading font-semibold mb-3">Customer Service</h3>
            <ul className="space-y-2 text-sm text-theme-muted">
              <li>
                <Link href="/policies/shipping" className="hover:text-theme-primary transition-colors">
                  Shipping Policy
                </Link>
              </li>
              <li>
                <Link href="/policies/returns" className="hover:text-theme-primary transition-colors">
                  Returns Policy
                </Link>
              </li>
              <li>
                <Link href="/policies/privacy" className="hover:text-theme-primary transition-colors">
                  Privacy Policy
                </Link>
              </li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <h3 className="text-sm font-heading font-semibold mb-3">Account</h3>
            <ul className="space-y-2 text-sm text-theme-muted">
              <li>
                <Link href="/account/login" className="hover:text-theme-primary transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <Link href="/account/orders" className="hover:text-theme-primary transition-colors">
                  Order Tracking
                </Link>
              </li>
              <li>
                <Link href="/account/wishlist" className="hover:text-theme-primary transition-colors">
                  Wishlist
                </Link>
              </li>
            </ul>
          </div>

          {/* About */}
          <div>
            <h3 className="text-sm font-heading font-semibold mb-3">About</h3>
            <ul className="space-y-2 text-sm text-theme-muted">
              <li>
                <Link href="/policies/terms" className="hover:text-theme-primary transition-colors">
                  Terms &amp; Conditions
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 pt-6 border-t border-theme flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-theme-muted">
          <p>&copy; {new Date().getFullYear()} {store.name}. All rights reserved.</p>
          <p>Powered by Dropshipping Platform</p>
        </div>
      </div>
    </footer>
  );
}
