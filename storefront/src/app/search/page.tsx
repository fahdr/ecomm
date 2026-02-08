/**
 * Search page for the storefront.
 *
 * Provides a full-featured product search with text query, price range
 * filters, sort options, and paginated results. The search form submits
 * via URL query parameters so results are bookmarkable and shareable.
 *
 * **For Developers:**
 *   This page combines server and client components. The outer shell
 *   is a server component that resolves the store and reads initial
 *   search params. The interactive search form and results are rendered
 *   by the ``SearchContent`` client component which uses the public
 *   search API endpoint.
 *
 * **For QA Engineers:**
 *   - Empty query shows all products.
 *   - Price filters are optional and cumulative.
 *   - Sort options: relevance, price_asc, price_desc, newest.
 *   - Pagination buttons appear when more than 12 results exist.
 *   - No authentication required.
 *   - URL reflects current search state (query, page, sort, etc.).
 *
 * **For End Users:**
 *   Search for products by name or description. Filter by price and
 *   sort results to find what you want quickly.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { fetchStore } from "@/lib/store";
import { SearchContent } from "./search-content";

/**
 * Search page server component. Resolves the store and renders
 * the client-side search interface.
 *
 * @param props - Page props from Next.js.
 * @param props.searchParams - URL search parameters including ``q``, ``page``, etc.
 * @returns The search page with interactive form and results.
 */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    page?: string;
    sort?: string;
    min_price?: string;
    max_price?: string;
  }>;
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

  const sp = await searchParams;

  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SearchContent
          storeSlug={store.slug}
          initialQuery={sp.q || ""}
          initialPage={sp.page || "1"}
          initialSort={sp.sort || "relevance"}
          initialMinPrice={sp.min_price || ""}
          initialMaxPrice={sp.max_price || ""}
        />
      </div>
    </div>
  );
}
