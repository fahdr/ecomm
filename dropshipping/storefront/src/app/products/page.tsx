/**
 * Product listing page for the storefront.
 *
 * Displays all active products for the store in a paginated grid.
 * Products are fetched server-side from the public API for SEO.
 *
 * **For Developers:**
 *   This is a server component. The store slug comes from the
 *   ``x-store-slug`` header. Pagination uses ``?page=`` query param.
 *
 * **For QA Engineers:**
 *   - Only active products are shown.
 *   - Default pagination: 12 products per page.
 *   - Previous/Next buttons appear when there are multiple pages.
 *   - Visiting without a valid store slug shows "Store not found".
 *
 * **For End Users:**
 *   Browse all available products. Use the pagination controls to
 *   navigate through the catalog.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import { AnimatedProductGrid } from "@/components/animated-product-grid";
import type { PaginatedProducts } from "@/lib/types";

/**
 * Product listing page server component.
 *
 * @param props - Page props from Next.js.
 * @param props.searchParams - URL search parameters including ``page``.
 * @returns A page with the product grid and pagination controls.
 */
export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  if (!slug) {
    notFound();
  }

  const store = await fetchStore(slug);
  if (!store) {
    notFound();
  }

  const params = await searchParams;
  const page = Math.max(1, parseInt(params.page || "1"));
  const perPage = 12;

  const { data: productsData } = await api.get<PaginatedProducts>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}/products?page=${page}&per_page=${perPage}`
  );

  const products = productsData?.items ?? [];
  const totalPages = productsData?.pages ?? 1;

  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold tracking-tight mb-8">All Products</h2>

        <AnimatedProductGrid products={products} />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-12 flex items-center justify-center gap-4">
            {page > 1 ? (
              <Link
                href={`/products?page=${page - 1}`}
                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
              >
                &larr; Previous
              </Link>
            ) : (
              <span className="px-4 py-2 rounded-lg border border-zinc-100 dark:border-zinc-900 text-sm font-medium text-zinc-300 dark:text-zinc-700">
                &larr; Previous
              </span>
            )}

            <span className="text-sm text-zinc-500 dark:text-zinc-400">
              Page {page} of {totalPages}
            </span>

            {page < totalPages ? (
              <Link
                href={`/products?page=${page + 1}`}
                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
              >
                Next &rarr;
              </Link>
            ) : (
              <span className="px-4 py-2 rounded-lg border border-zinc-100 dark:border-zinc-900 text-sm font-medium text-zinc-300 dark:text-zinc-700">
                Next &rarr;
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
