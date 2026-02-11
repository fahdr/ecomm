/**
 * Product grid component for the storefront with theme-aware styling.
 *
 * Renders a responsive grid of product cards with images, titles, and prices.
 * Each card links to the product detail page. All visual elements use
 * theme-driven CSS classes so the grid adapts to the store's active theme.
 *
 * **For Developers:**
 *   This is a server component. Product data is passed as props.
 *   Links use the product slug for SEO-friendly URLs. Cards use the
 *   ``theme-card`` utility class (defined in globals.css) for consistent
 *   border, background, radius, and hover effects. Headings use
 *   ``font-heading`` to inherit the theme's heading typeface. The grid
 *   container uses ``animate-fade-in`` for a smooth entrance animation.
 *
 * **For QA Engineers:**
 *   - Products without images show a placeholder icon.
 *   - Compare-at prices show with a strikethrough in ``text-theme-muted``.
 *   - Empty grid shows a "No products" message.
 *   - Cards use ``theme-card`` class for theme-driven border, surface, and hover.
 *   - Product titles use ``font-heading`` from the theme's typography config.
 *   - Price uses ``text-theme-primary`` for the selling price.
 *   - Image hover scale effect is preserved.
 *
 * **For Project Managers:**
 *   The product grid is used across multiple pages (homepage, category,
 *   search results). Its theme-aware styling ensures a consistent branded
 *   experience wherever products are displayed.
 *
 * **For End Users:**
 *   Browse products in the grid. Click any product to see its details.
 */

import Link from "next/link";
import type { Product } from "@/lib/types";

/**
 * Product card component showing image, title, and price.
 *
 * Uses ``theme-card`` for theme-driven surface color, border, radius,
 * and hover shadow. Product title uses ``font-heading`` and price uses
 * ``text-theme-primary`` to match the store's active theme.
 *
 * @param props - Component props.
 * @param props.product - The product data to display.
 * @returns A linked card element for the product.
 */
/**
 * Check if a product was created within the last 7 days.
 */
function isNew(createdAt: string): boolean {
  const created = new Date(createdAt);
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  return created > sevenDaysAgo;
}

/**
 * Calculate the discount percentage between compare_at_price and price.
 */
function discountPercent(price: string, compareAtPrice: string): number {
  const p = Number(price);
  const cp = Number(compareAtPrice);
  if (!cp || cp <= p) return 0;
  return Math.round(((cp - p) / cp) * 100);
}

function ProductCard({ product }: { product: Product }) {
  const showNew = product.created_at ? isNew(product.created_at) : false;
  const showSale = !!product.compare_at_price;
  const discount = showSale ? discountPercent(product.price, product.compare_at_price!) : 0;

  return (
    <Link href={`/products/${product.slug}`} className="group">
      <div className="theme-card overflow-hidden">
        {/* Image with badges */}
        <div className="relative aspect-square bg-theme-surface overflow-hidden">
          {product.images && product.images.length > 0 ? (
            <img
              src={product.images[0]}
              alt={product.title}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center">
              <div className="w-16 h-16 rounded-full bg-theme-surface border border-theme" />
            </div>
          )}

          {/* Badges */}
          <div className="absolute top-2 left-2 flex flex-col gap-1">
            {showNew && (
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-theme-primary text-white">
                New
              </span>
            )}
            {showSale && discount > 0 && (
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-red-500 text-white">
                -{discount}%
              </span>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="p-4">
          <h4 className="font-heading font-medium text-sm line-clamp-2 mb-2">
            {product.title}
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-theme-primary">
              ${Number(product.price).toFixed(2)}
            </span>
            {product.compare_at_price && (
              <span className="text-sm text-theme-muted line-through">
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
 * Uses ``animate-fade-in`` on the grid container for a smooth entrance
 * animation. Each product is rendered as a {@link ProductCard} with
 * theme-aware styling.
 *
 * @param props - Component props.
 * @param props.products - Array of products to display.
 * @returns A grid of ProductCard components, or an empty state message.
 */
export function ProductGrid({ products }: { products: Product[] }) {
  if (products.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-theme-muted">
          No products available yet. Check back soon!
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
