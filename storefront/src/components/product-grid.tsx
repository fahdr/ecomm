/**
 * Product grid component for the storefront.
 *
 * Renders a responsive grid of product cards with images, titles, and prices.
 * Each card links to the product detail page.
 *
 * **For Developers:**
 *   This is a server component. Product data is passed as props.
 *   Links use the product slug for SEO-friendly URLs.
 *
 * **For QA Engineers:**
 *   - Products without images show a placeholder.
 *   - Compare-at prices show with a strikethrough.
 *   - Empty grid shows a "No products" message.
 *
 * **For End Users:**
 *   Browse products in the grid. Click any product to see its details.
 */

import Link from "next/link";
import type { Product } from "@/lib/types";

/**
 * Product card component showing image, title, and price.
 *
 * @param props - Component props.
 * @param props.product - The product data to display.
 * @returns A linked card element for the product.
 */
function ProductCard({ product }: { product: Product }) {
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

/**
 * Product grid displaying a list of products in a responsive layout.
 *
 * @param props - Component props.
 * @param props.products - Array of products to display.
 * @returns A grid of ProductCard components, or an empty state message.
 */
export function ProductGrid({ products }: { products: Product[] }) {
  if (products.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-zinc-500 dark:text-zinc-400">
          No products available yet. Check back soon!
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
