/**
 * Client-side search content component.
 *
 * Handles interactive search form, filter controls, results display,
 * and pagination. Communicates with the public search API endpoint
 * and updates the browser URL to keep search state bookmarkable.
 *
 * **For Developers:**
 *   This is a client component (``"use client"``). It fetches search
 *   results via the ``api.get`` helper and manages local state for
 *   the query, filters, sort, and pagination. URL updates use
 *   ``window.history.replaceState`` to avoid full-page reloads.
 *
 * **For QA Engineers:**
 *   - Submitting the form triggers a search API call.
 *   - Changing sort or page triggers a new search.
 *   - Loading state shows a spinner overlay.
 *   - Error state shows a human-readable error message.
 *   - No results shows a "no products found" message.
 *
 * **For End Users:**
 *   Type your search, apply filters, and browse results. Click a
 *   product to see its full details.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PaginatedSearchResults, SearchProduct } from "@/lib/types";

/**
 * Props for the SearchContent component.
 */
interface SearchContentProps {
  /** The store slug for API calls. */
  storeSlug: string;
  /** Initial query from URL params. */
  initialQuery: string;
  /** Initial page from URL params. */
  initialPage: string;
  /** Initial sort from URL params. */
  initialSort: string;
  /** Initial minimum price from URL params. */
  initialMinPrice: string;
  /** Initial maximum price from URL params. */
  initialMaxPrice: string;
}

/**
 * Interactive search form and results component.
 *
 * @param props - Search configuration from the server component.
 * @returns The complete search interface with form, filters, and results grid.
 */
export function SearchContent({
  storeSlug,
  initialQuery,
  initialPage,
  initialSort,
  initialMinPrice,
  initialMaxPrice,
}: SearchContentProps) {
  const [query, setQuery] = useState(initialQuery);
  const [sort, setSort] = useState(initialSort);
  const [minPrice, setMinPrice] = useState(initialMinPrice);
  const [maxPrice, setMaxPrice] = useState(initialMaxPrice);
  const [page, setPage] = useState(parseInt(initialPage) || 1);
  const [results, setResults] = useState<SearchProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const perPage = 12;

  /**
   * Execute a search against the public search API.
   *
   * @param searchQuery - The text query.
   * @param searchPage - The page number.
   * @param searchSort - The sort order.
   * @param searchMin - The minimum price filter.
   * @param searchMax - The maximum price filter.
   */
  const doSearch = useCallback(
    async (
      searchQuery: string,
      searchPage: number,
      searchSort: string,
      searchMin: string,
      searchMax: string
    ) => {
      setLoading(true);
      setError(null);

      /* Build query string for the search API. */
      const params = new URLSearchParams();
      if (searchQuery) params.set("query", searchQuery);
      params.set("page", String(searchPage));
      params.set("per_page", String(perPage));
      params.set("sort_by", searchSort);
      if (searchMin) params.set("min_price", searchMin);
      if (searchMax) params.set("max_price", searchMax);

      const { data, error: apiError } = await api.get<PaginatedSearchResults>(
        `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/search?${params.toString()}`
      );

      if (apiError) {
        setError(apiError.message || "Search failed. Please try again.");
        setResults([]);
        setTotal(0);
        setTotalPages(1);
      } else if (data) {
        setResults(data.items);
        setTotal(data.total);
        setTotalPages(data.pages);
      }

      setLoading(false);
      setSearched(true);

      /* Update the browser URL without a full navigation. */
      const urlParams = new URLSearchParams();
      if (searchQuery) urlParams.set("q", searchQuery);
      if (searchPage > 1) urlParams.set("page", String(searchPage));
      if (searchSort !== "relevance") urlParams.set("sort", searchSort);
      if (searchMin) urlParams.set("min_price", searchMin);
      if (searchMax) urlParams.set("max_price", searchMax);
      const qs = urlParams.toString();
      window.history.replaceState({}, "", `/search${qs ? `?${qs}` : ""}`);
    },
    [storeSlug]
  );

  /* Run initial search if there is a query or on first mount. */
  useEffect(() => {
    if (initialQuery) {
      doSearch(initialQuery, parseInt(initialPage) || 1, initialSort, initialMinPrice, initialMaxPrice);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Handle form submit. */
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    doSearch(query, 1, sort, minPrice, maxPrice);
  }

  /** Navigate to a different page. */
  function goToPage(newPage: number) {
    setPage(newPage);
    doSearch(query, newPage, sort, minPrice, maxPrice);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /** Handle sort change. */
  function handleSortChange(newSort: string) {
    setSort(newSort);
    setPage(1);
    doSearch(query, 1, newSort, minPrice, maxPrice);
  }

  return (
    <>
      {/* Search form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Main search input */}
          <div className="relative flex-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-zinc-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search products..."
              className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:focus:ring-zinc-500"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 dark:bg-zinc-100 px-6 py-3 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors shrink-0"
          >
            Search
          </button>
        </div>

        {/* Filters row */}
        <div className="mt-4 flex flex-wrap items-end gap-4">
          {/* Price range */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
              Price
            </label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="Min"
              className="w-24 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-400"
            />
            <span className="text-zinc-400">-</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="Max"
              className="w-24 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-400"
            />
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
              Sort
            </label>
            <select
              value={sort}
              onChange={(e) => handleSortChange(e.target.value)}
              className="rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-400"
            >
              <option value="relevance">Relevance</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="newest">Newest First</option>
            </select>
          </div>
        </div>
      </form>

      {/* Error message */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 dark:border-zinc-600 border-t-zinc-900 dark:border-t-zinc-100" />
        </div>
      )}

      {/* Results */}
      {!loading && searched && (
        <>
          {/* Results count */}
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {total === 0
                ? "No products found"
                : `${total} product${total !== 1 ? "s" : ""} found`}
              {query && (
                <span>
                  {" "}
                  for &ldquo;<span className="font-medium text-zinc-700 dark:text-zinc-300">{query}</span>&rdquo;
                </span>
              )}
            </p>
          </div>

          {/* Product grid */}
          {results.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {results.map((product) => (
                <SearchProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <p className="text-zinc-500 dark:text-zinc-400">
                Try a different search term or adjust your filters.
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-12 flex items-center justify-center gap-4">
              <button
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                &larr; Previous
              </button>
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-800 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next &rarr;
              </button>
            </div>
          )}
        </>
      )}

      {/* Empty state before search */}
      {!loading && !searched && (
        <div className="text-center py-16">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1}
            stroke="currentColor"
            className="mx-auto h-16 w-16 text-zinc-300 dark:text-zinc-700 mb-4"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <h3 className="text-lg font-medium mb-2">Search our catalog</h3>
          <p className="text-zinc-500 dark:text-zinc-400">
            Enter a search term above to find products.
          </p>
        </div>
      )}
    </>
  );
}

/**
 * Search result product card.
 *
 * Renders a single search result as a card with image, title, and price.
 * Follows the same visual pattern as the ProductGrid cards.
 *
 * @param props - Component props.
 * @param props.product - The search result product data.
 * @returns A linked card element for the search result.
 */
function SearchProductCard({ product }: { product: SearchProduct }) {
  return (
    <Link href={`/products/${product.slug}`} className="group">
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden transition-shadow hover:shadow-md">
        {/* Image */}
        <div className="aspect-square bg-zinc-100 dark:bg-zinc-900 overflow-hidden">
          {product.images && product.images.length > 0 ? (
            <img
              src={product.images[0]}
              alt={product.title}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center">
              <div className="w-16 h-16 rounded-full bg-zinc-200 dark:bg-zinc-700" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="p-4">
          <h4 className="font-medium text-sm line-clamp-2 mb-2">
            {product.title}
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">
              ${Number(product.price).toFixed(2)}
            </span>
            {product.compare_at_price && (
              <span className="text-sm text-zinc-400 line-through">
                ${Number(product.compare_at_price).toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
