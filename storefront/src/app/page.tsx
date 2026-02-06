/**
 * Storefront homepage.
 *
 * Displays the store's hero section with name, description, and niche,
 * plus a grid of active products fetched from the public API.
 *
 * If no store is resolved (missing ``?store=`` param or unknown slug),
 * a "Store not found" message is shown via the not-found page.
 *
 * **For Developers:**
 *   This is a server component. Store data is read from the
 *   ``x-store-slug`` header set by middleware, then fetched from the API.
 *   Products are fetched server-side for SEO.
 *
 * **For QA Engineers:**
 *   - With a valid slug: shows store name, description, niche, and products.
 *   - Without a slug: shows "Store not found" with instructions.
 *   - With an invalid slug: shows "Store not found".
 *   - Only active products are displayed.
 *
 * **For End Users:**
 *   This is the main page of your store. Customers see your store name,
 *   description, and products here.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import { ProductGrid } from "@/components/product-grid";
import type { PaginatedProducts } from "@/lib/types";

/**
 * Homepage server component.
 *
 * @returns The store homepage with hero section and product grid.
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

  // Fetch active products for this store
  const { data: productsData } = await api.get<PaginatedProducts>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}/products?per_page=12`
  );

  const products = productsData?.items ?? [];

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-zinc-50 dark:bg-zinc-900 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Welcome to {store.name}
          </h2>
          {store.description && (
            <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
              {store.description}
            </p>
          )}
          <div className="mt-6">
            <span className="inline-flex items-center rounded-full bg-zinc-200 dark:bg-zinc-700 px-3 py-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              {store.niche}
            </span>
          </div>
        </div>
      </section>

      {/* Product Grid */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-2xl font-bold tracking-tight">Products</h3>
            {productsData && productsData.total > 12 && (
              <Link
                href="/products"
                className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
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
