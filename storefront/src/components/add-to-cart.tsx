/**
 * Add to Cart button component for the product detail page.
 *
 * Allows customers to select a variant (if applicable) and add the
 * product to their cart with a specified quantity.
 *
 * **For Developers:**
 *   This is a client component that uses the cart context. It receives
 *   product data as props from the server-rendered product detail page.
 *
 * **For QA Engineers:**
 *   - Without variants: adds the base product to the cart.
 *   - With variants: requires selecting a variant before adding.
 *   - Out-of-stock variants are disabled.
 *   - Quantity defaults to 1, minimum 1.
 *   - Shows a brief "Added!" confirmation after adding.
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
  id: string;
  name: string;
  sku: string | null;
  price: string | null;
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
 * Add to Cart interactive component.
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

  const effectivePrice = selectedVariant?.price
    ? Number(selectedVariant.price)
    : Number(price);

  const isOutOfStock =
    selectedVariant && selectedVariant.inventory_count <= 0;

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
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
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
                    ? "border-zinc-900 dark:border-zinc-100 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900"
                    : variant.inventory_count <= 0
                      ? "border-zinc-200 dark:border-zinc-800 text-zinc-300 dark:text-zinc-700 cursor-not-allowed"
                      : "border-zinc-300 dark:border-zinc-700 hover:border-zinc-900 dark:hover:border-zinc-100"
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
        <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
          Quantity
        </label>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setQuantity((q) => Math.max(1, q - 1))}
            className="h-10 w-10 rounded-lg border border-zinc-300 dark:border-zinc-700 flex items-center justify-center hover:bg-zinc-50 dark:hover:bg-zinc-900"
          >
            -
          </button>
          <span className="w-12 text-center font-medium">{quantity}</span>
          <button
            onClick={() => setQuantity((q) => q + 1)}
            className="h-10 w-10 rounded-lg border border-zinc-300 dark:border-zinc-700 flex items-center justify-center hover:bg-zinc-50 dark:hover:bg-zinc-900"
          >
            +
          </button>
        </div>
      </div>

      {/* Add to Cart Button */}
      <button
        onClick={handleAdd}
        disabled={isOutOfStock || false}
        className={`w-full rounded-lg px-6 py-3 text-sm font-medium transition-colors ${
          added
            ? "bg-green-600 text-white"
            : isOutOfStock
              ? "bg-zinc-300 dark:bg-zinc-700 text-zinc-500 cursor-not-allowed"
              : "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200"
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
