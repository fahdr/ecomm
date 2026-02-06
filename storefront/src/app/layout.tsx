/**
 * Root layout for the storefront app.
 *
 * Resolves the store slug from the ``x-store-slug`` header (set by
 * middleware), fetches store data from the backend, and renders the
 * store-aware header and footer. If no store can be resolved, the
 * children (page) handle showing a "store not found" state.
 *
 * **For Developers:**
 *   This is a server component. Store data is fetched at request time
 *   via the public API. The store object is passed to children via
 *   the StoreProvider context so client components can access it.
 *
 * **For QA Engineers:**
 *   - The page title and meta description are set dynamically from store data.
 *   - Without a ``?store=`` param (local dev), the layout renders without
 *     store branding.
 *
 * **For End Users:**
 *   The header shows your store name and the footer displays basic
 *   store information.
 */

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import "./globals.css";
import { fetchStore } from "@/lib/store";
import type { Store } from "@/lib/types";
import { StoreProvider } from "@/contexts/store-context";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

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
 * Root layout component that wraps all pages with store context,
 * header, and footer.
 *
 * @param props - Layout props containing children to render.
 * @param props.children - The page content to render inside the layout.
 * @returns The complete HTML document with store-aware chrome.
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  let store: Store | null = null;
  if (slug) {
    store = await fetchStore(slug);
  }

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <StoreProvider store={store}>
          {store && <StoreHeader store={store} />}
          <main className="flex-1">{children}</main>
          {store && <StoreFooter store={store} />}
        </StoreProvider>
      </body>
    </html>
  );
}

/**
 * Store header component displaying the store name and navigation.
 *
 * @param props - Component props.
 * @param props.store - The resolved store data.
 * @returns A header element with store branding.
 */
function StoreHeader({ store }: { store: Store }) {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">{store.name}</h1>
          <nav className="flex items-center gap-6">
            <span className="text-sm text-zinc-500 dark:text-zinc-400">
              {store.niche}
            </span>
          </nav>
        </div>
      </div>
    </header>
  );
}

/**
 * Store footer component displaying store info and copyright.
 *
 * @param props - Component props.
 * @param props.store - The resolved store data.
 * @returns A footer element with store information.
 */
function StoreFooter({ store }: { store: Store }) {
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800 py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
          <p>&copy; {new Date().getFullYear()} {store.name}. All rights reserved.</p>
          <p>Powered by Dropshipping Platform</p>
        </div>
      </div>
    </footer>
  );
}
