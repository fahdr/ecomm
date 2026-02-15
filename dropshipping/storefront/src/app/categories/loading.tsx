/**
 * Loading skeleton for the categories listing page.
 *
 * Displayed by Next.js automatically while the server component
 * fetches category data. Shows shimmer category cards.
 *
 * @module app/categories/loading
 */

export default function CategoriesLoading() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Title skeleton */}
        <div className="h-9 w-56 rounded-lg bg-theme-border animate-pulse mb-3" />
        <div className="h-5 w-80 rounded bg-theme-border animate-pulse mb-8" />

        {/* Category grid skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="theme-card overflow-hidden animate-pulse">
              <div className="aspect-[16/9] bg-theme-border" />
              <div className="p-5 space-y-3">
                <div className="h-5 rounded bg-theme-border w-2/3" />
                <div className="h-4 rounded bg-theme-border w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
