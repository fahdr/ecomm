/**
 * Category detail page for the storefront.
 *
 * Shows all active products within a specific category with pagination.
 * Products are fetched from the public API by category slug.
 *
 * **For Developers:**
 *   This is a server component. The category slug comes from the URL
 *   parameter. The store slug comes from the ``x-store-slug`` header.
 *   Dynamic SEO metadata is generated from the category data.
 *
 * **For QA Engineers:**
 *   - Only active products within the category are shown.
 *   - Default pagination: 12 products per page.
 *   - Visiting a non-existent category slug shows 404.
 *   - Breadcrumb navigation shows Home > Categories > Category Name.
 *   - The page title updates to the category name.
 *
 * **For End Users:**
 *   Browse all products in a specific category. Use pagination to see
 *   more results.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import { ProductGrid } from "@/components/product-grid";
import type { PaginatedCategoryProducts } from "@/lib/types";

/**
 * Generate dynamic metadata for the category detail page.
 *
 * @param props - Page props containing the category slug parameter.
 * @returns Metadata object with category name as title.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const headersList = await headers();
  const storeSlug = headersList.get("x-store-slug");

  if (!storeSlug) {
    return { title: "Category Not Found" };
  }

  const { slug: categorySlug } = await params;
  const { data } = await api.get<PaginatedCategoryProducts>(
    `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/categories/${encodeURIComponent(categorySlug)}/products?per_page=1`
  );

  if (!data?.category) {
    return { title: "Category Not Found" };
  }

  return {
    title: data.category.name,
    description:
      data.category.description ||
      `Browse ${data.category.name} products`,
  };
}

/**
 * Category detail page server component.
 *
 * @param props - Page props from Next.js.
 * @param props.params - URL parameters containing the category slug.
 * @param props.searchParams - URL search parameters including ``page``.
 * @returns A page with the category header, breadcrumbs, product grid, and pagination.
 */
export default async function CategoryDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const headersList = await headers();
  const storeSlug = headersList.get("x-store-slug");

  if (!storeSlug) {
    notFound();
  }

  const store = await fetchStore(storeSlug);
  if (!store) {
    notFound();
  }

  const { slug: categorySlug } = await params;
  const sp = await searchParams;
  const page = Math.max(1, parseInt(sp.page || "1"));
  const perPage = 12;

  const { data } = await api.get<PaginatedCategoryProducts>(
    `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/categories/${encodeURIComponent(categorySlug)}/products?page=${page}&per_page=${perPage}`
  );

  if (!data?.category) {
    notFound();
  }

  const category = data.category;
  const products = data.items ?? [];
  const totalPages = data.pages ?? 1;

  /*
   * Map category products (which have the same shape as Product from
   * the public API) to the Product interface expected by ProductGrid.
   */
  const mappedProducts = products.map((p) => ({
    ...p,
    price: String(p.price),
    compare_at_price: p.compare_at_price ? String(p.compare_at_price) : null,
    images: p.images ?? null,
    seo_title: null,
    seo_description: null,
    created_at: "",
    variants: [],
  }));

  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="mb-8 text-sm text-zinc-500 dark:text-zinc-400">
          <Link href="/" className="hover:text-zinc-900 dark:hover:text-zinc-100">
            Home
          </Link>
          <span className="mx-2">/</span>
          <Link
            href="/categories"
            className="hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Categories
          </Link>
          <span className="mx-2">/</span>
          <span className="text-zinc-900 dark:text-zinc-100">
            {category.name}
          </span>
        </nav>

        {/* Category header */}
        <div className="mb-10">
          <h2 className="text-3xl font-bold tracking-tight">{category.name}</h2>
          {category.description && (
            <p className="mt-2 text-zinc-600 dark:text-zinc-400 max-w-2xl">
              {category.description}
            </p>
          )}
          <p className="mt-1 text-sm text-zinc-400 dark:text-zinc-500">
            {data.total} product{data.total !== 1 ? "s" : ""}
          </p>
        </div>

        {/* Product grid */}
        <ProductGrid products={mappedProducts} />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-12 flex items-center justify-center gap-4">
            {page > 1 ? (
              <Link
                href={`/categories/${categorySlug}?page=${page - 1}`}
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
                href={`/categories/${categorySlug}?page=${page + 1}`}
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
