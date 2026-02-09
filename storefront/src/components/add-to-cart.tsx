/**
 * Add to Cart button component for the product detail page with
 * theme-aware styling.
 *
 * Allows customers to select a variant (if applicable) and add the
 * product to their cart with a specified quantity. All interactive
 * elements use theme-driven CSS classes for consistent branding.
 *
 * **For Developers:**
 *   This is a client component that uses the cart context. It receives
 *   product data as props from the server-rendered product detail page.
 *   The main "Add to Cart" button uses the ``btn-primary`` utility class
 *   (themed background, text, radius). Variant selector buttons use
 *   ``border-theme`` for borders and ``text-theme-primary`` for the
 *   selected state highlight. Quantity controls use ``border-theme``.
 *
 * **For QA Engineers:**
 *   - Without variants: adds the base product to the cart.
 *   - With variants: requires selecting a variant before adding.
 *   - Out-of-stock variants are disabled with muted styling.
 *   - Quantity defaults to 1, minimum 1.
 *   - Shows a brief "Added!" confirmation (green) after adding.
 *   - Selected variant uses ``text-theme-primary`` highlight.
 *   - Main button uses ``btn-primary`` class for theme colors.
 *   - Variant and quantity borders use ``border-theme``.
 *
 * **For Project Managers:**
 *   The add-to-cart component is the primary conversion point on the
 *   product page. Theme-aware styling ensures it matches the store's
 *   branding, reinforcing trust and visual consistency.
 *
 * **For End Users:**
 *   Select your preferred option (if available) and click "Add to Cart"
 *   to add the product to your shopping cart.
 */

"use client";

import { useState } from "react";
import { useCart } from "@/contexts/cart-context";

/**
 * Variant data passed from the server component.
 */
interface Variant {
  /** Unique variant identifier (UUID). */
  id: string;
  /** Display name of the variant (e.g. "Large", "Blue"). */
  name: string;
  /** Optional stock-keeping unit identifier. */
  sku: string | null;
  /** Optional price override as a string decimal. */
  price: string | null;
  /** Number of units available in stock. */
  inventory_count: number;
}

/**
 * Props for the AddToCart component.
 */
interface AddToCartProps {
  /** Product UUID. */
  productId: string;
  /** Product display title. */
  title: string;
  /** Product URL slug. */
  slug: string;
  /** Base price as a string decimal. */
  price: string;
  /** First product image URL, or null. */
  image: string | null;
  /** Available variants. */
  variants: Variant[];
}

/**
 * Add to Cart interactive component with theme-aware styling.
 *
 * Renders variant selector buttons, a quantity input, and the main
 * add-to-cart button. All elements adapt to the store's active theme
 * via CSS custom properties.
 *
 * @param props - Product data for the cart item.
 * @returns Variant selector (if applicable), quantity input, and add button.
 */
export function AddToCart({
  productId,
  title,
  slug,
  price,
  image,
  variants,
}: AddToCartProps) {
  const { addItem } = useCart();
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(
    variants.length > 0 ? variants[0] : null
  );
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  /** Effective price: uses variant override if available, otherwise base price. */
  const effectivePrice = selectedVariant?.price
    ? Number(selectedVariant.price)
    : Number(price);

  /** Whether the currently selected variant is out of stock. */
  const isOutOfStock =
    selectedVariant && selectedVariant.inventory_count <= 0;

  /**
   * Handle adding the product (with selected variant and quantity) to the cart.
   * Shows a brief "Added!" confirmation, then resets after 2 seconds.
   */
  function handleAdd() {
    addItem({
      productId,
      variantId: selectedVariant?.id || null,
      title,
      variantName: selectedVariant?.name || null,
      price: effectivePrice,
      quantity,
      image,
      slug,
    });
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  }

  return (
    <div className="mt-8 space-y-4">
      {/* Variant Selector */}
      {variants.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-theme-muted mb-2">
            Select Option
          </label>
          <div className="flex flex-wrap gap-2">
            {variants.map((variant) => (
              <button
                key={variant.id}
                onClick={() => setSelectedVariant(variant)}
                disabled={variant.inventory_count <= 0}
                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  selectedVariant?.id === variant.id
                    ? "border-theme bg-theme-primary text-(--theme-primary-text)"
                    : variant.inventory_count <= 0
                      ? "border-theme text-theme-muted opacity-50 cursor-not-allowed"
                      : "border-theme hover:text-theme-primary hover:border-theme-primary"
                }`}
              >
                {variant.name}
                {variant.inventory_count <= 0 && " (Out of stock)"}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quantity */}
      <div>
        <label className="block text-sm font-medium text-theme-muted mb-2">
          Quantity
        </label>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setQuantity((q) => Math.max(1, q - 1))}
            className="h-10 w-10 rounded-lg border border-theme flex items-center justify-center hover:bg-theme-surface transition-colors"
          >
            -
          </button>
          <span className="w-12 text-center font-medium">{quantity}</span>
          <button
            onClick={() => setQuantity((q) => q + 1)}
            className="h-10 w-10 rounded-lg border border-theme flex items-center justify-center hover:bg-theme-surface transition-colors"
          >
            +
          </button>
        </div>
      </div>

      {/* Add to Cart Button */}
      <button
        onClick={handleAdd}
        disabled={isOutOfStock || false}
        className={`w-full px-6 py-3 text-sm font-medium transition-colors ${
          added
            ? "bg-green-600 text-white rounded-lg"
            : isOutOfStock
              ? "bg-theme-surface border border-theme text-theme-muted cursor-not-allowed rounded-lg"
              : "btn-primary"
        }`}
      >
        {added
          ? "Added to Cart!"
          : isOutOfStock
            ? "Out of Stock"
            : `Add to Cart — $${(effectivePrice * quantity).toFixed(2)}`}
      </button>
    </div>
  );
}
