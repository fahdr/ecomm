/**
 * Storefront homepage with theme-aware block rendering.
 *
 * Resolves the store slug from request headers, fetches the store's
 * active theme from the public API, and renders the homepage using the
 * theme's composable block system via {@link BlockRenderer}. If no
 * theme is available, falls back to a simple hero section with a
 * product grid.
 *
 * **For Developers:**
 *   This is a server component. The store slug is read from the
 *   ``x-store-slug`` header (set by middleware). Theme data is fetched
 *   from ``GET /api/v1/public/stores/{slug}/theme``. Products are
 *   always fetched server-side for SEO regardless of which rendering
 *   path is used (blocks vs. fallback).
 *
 * **For QA Engineers:**
 *   - With a valid slug and theme: renders blocks from the theme config
 *     via BlockRenderer, then appends the product grid below.
 *   - With a valid slug but no theme: renders a fallback hero section
 *     and product grid using theme-aware CSS classes.
 *   - Without a slug or with an invalid slug: shows "Store not found".
 *   - Only active products are displayed in the grid.
 *
 * **For Project Managers:**
 *   The homepage is now fully driven by the store's theme configuration.
 *   Store owners can control what blocks appear on their homepage via
 *   the Themes page in the dashboard. The fallback ensures stores
 *   without a custom theme still have a functional homepage.
 *
 * **For End Users:**
 *   This is the main page of your store. Customers see your branded
 *   homepage with the sections you've configured in your theme, plus
 *   a product grid showcasing your latest products.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import { ProductGrid } from "@/components/product-grid";
import { BlockRenderer } from "@/components/blocks/block-renderer";
import type { PaginatedProducts, StoreTheme } from "@/lib/types";

/**
 * Homepage server component.
 *
 * Fetches the store, its theme, and products, then renders the page
 * using either the theme's block system or a fallback layout.
 *
 * @returns The store homepage with theme blocks or fallback hero + product grid.
 */
export default async function HomePage() {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  if (!slug) {
    notFound();
  }

  const store = await fetchStore(slug);

  if (!store) {
    notFound();
  }

  // Fetch the store's active theme
  const { data: theme } = await api.get<StoreTheme>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}/theme`
  );

  // Fetch active products for this store
  const { data: productsData } = await api.get<PaginatedProducts>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}/products?per_page=12`
  );

  const products = productsData?.items ?? [];

  // If a theme with blocks is available, use the BlockRenderer
  if (theme && theme.blocks && theme.blocks.length > 0) {
    return (
      <div className="animate-fade-in">
        {/* Render theme blocks */}
        <BlockRenderer blocks={theme.blocks} />

        {/* Product grid (always shown below blocks) */}
        <section className="py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h3 className="font-heading text-2xl font-bold tracking-tight">
                Products
              </h3>
              {productsData && productsData.total > 12 && (
                <Link
                  href="/products"
                  className="text-sm font-medium text-theme-muted hover:text-theme-primary transition-colors"
                >
                  View all &rarr;
                </Link>
              )}
            </div>
            <ProductGrid products={products} />
          </div>
        </section>
      </div>
    );
  }

  // Fallback: no theme available, render a simple hero + product grid
  return (
    <div className="animate-fade-in">
      {/* Fallback Hero Section */}
      <section className="bg-theme-surface py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-4xl font-bold tracking-tight sm:text-5xl">
            Welcome to {store.name}
          </h2>
          {store.description && (
            <p className="mt-4 text-lg text-theme-muted max-w-2xl mx-auto">
              {store.description}
            </p>
          )}
          <div className="mt-6">
            <span className="inline-flex items-center rounded-full bg-theme-primary/10 text-theme-primary px-3 py-1 text-sm font-medium">
              {store.niche}
            </span>
          </div>
        </div>
      </section>

      {/* Product Grid */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-heading text-2xl font-bold tracking-tight">
              Products
            </h3>
            {productsData && productsData.total > 12 && (
              <Link
                href="/products"
                className="text-sm font-medium text-theme-muted hover:text-theme-primary transition-colors"
              >
                View all &rarr;
              </Link>
            )}
          </div>
          <ProductGrid products={products} />
        </div>
      </section>
    </div>
  );
}
