/**
 * Loading skeleton for the product detail page.
 *
 * Displayed by Next.js automatically while the server component
 * fetches product data. Shows a two-column layout with shimmer
 * placeholders for the image and product info.
 *
 * @module app/products/[slug]/loading
 */

export default function ProductDetailLoading() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16">
          {/* Image skeleton */}
          <div className="aspect-square rounded-xl bg-theme-border animate-pulse" />

          {/* Info skeleton */}
          <div className="space-y-6 animate-pulse">
            {/* Title */}
            <div className="space-y-3">
              <div className="h-8 rounded bg-theme-border w-3/4" />
              <div className="h-5 rounded bg-theme-border w-1/2" />
            </div>

            {/* Price */}
            <div className="h-10 rounded bg-theme-border w-32" />

            {/* Description */}
            <div className="space-y-2">
              <div className="h-4 rounded bg-theme-border w-full" />
              <div className="h-4 rounded bg-theme-border w-5/6" />
              <div className="h-4 rounded bg-theme-border w-3/4" />
            </div>

            {/* Variants */}
            <div className="flex gap-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-10 w-20 rounded-lg bg-theme-border" />
              ))}
            </div>

            {/* Button */}
            <div className="h-12 rounded-lg bg-theme-border w-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
