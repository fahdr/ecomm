/**
 * Loading skeleton for the products listing page.
 *
 * Displayed by Next.js automatically while the server component fetches
 * product data. Shows a shimmer grid of placeholder cards.
 *
 * @module app/products/loading
 */

export default function ProductsLoading() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Title skeleton */}
        <div className="h-9 w-48 rounded-lg bg-theme-border animate-pulse mb-8" />

        {/* Product grid skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="theme-card overflow-hidden animate-pulse">
              <div className="aspect-square bg-theme-border" />
              <div className="p-4 space-y-3">
                <div className="h-4 rounded bg-theme-border w-3/4" />
                <div className="h-5 rounded bg-theme-border w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
