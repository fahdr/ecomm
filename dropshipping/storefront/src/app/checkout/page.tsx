/**
 * Multi-step checkout page for the storefront.
 *
 * Collects shipping address, optional discount code, displays an order
 * summary with real-time tax calculation, and submits the full checkout
 * to the backend API which creates a Stripe session.
 *
 * **For Developers:**
 *   Client component that reads cart context and store context.
 *   Calls three backend endpoints: validate-discount, calculate-tax,
 *   and checkout. Redirects to Stripe on success.
 *
 * **For QA Engineers:**
 *   - All required fields must be filled before checkout is enabled.
 *   - Discount code shows success/error inline.
 *   - Tax recalculates when address country/state/postal changes.
 *   - Gift card validation shows balance if valid.
 *   - Empty cart redirects to /cart.
 *
 * **For End Users:**
 *   Enter your shipping details, apply any discount or gift card codes,
 *   review your order totals, and proceed to secure payment.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCart } from "@/contexts/cart-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import type {
  ShippingAddress,
  CheckoutResponse,
  DiscountValidation,
  TaxCalculation,
  GiftCardValidation,
} from "@/lib/types";

/** ISO 3166-1 countries commonly used in e-commerce. */
const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "GB", name: "United Kingdom" },
  { code: "AU", name: "Australia" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "JP", name: "Japan" },
  { code: "NL", name: "Netherlands" },
  { code: "SE", name: "Sweden" },
  { code: "NZ", name: "New Zealand" },
  { code: "IE", name: "Ireland" },
  { code: "SG", name: "Singapore" },
];

/**
 * Checkout page client component.
 *
 * @returns Multi-section checkout form with address, discounts, and summary.
 */
export default function CheckoutPage() {
  const router = useRouter();
  const { items, cartTotal, clearCart } = useCart();
  const store = useStore();

  // --- Form State ---
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState<ShippingAddress>({
    name: "",
    line1: "",
    line2: "",
    city: "",
    state: "",
    postal_code: "",
    country: "US",
    phone: "",
  });

  // --- Discount ---
  const [discountCode, setDiscountCode] = useState("");
  const [discountResult, setDiscountResult] = useState<DiscountValidation | null>(null);
  const [discountLoading, setDiscountLoading] = useState(false);

  // --- Gift Card ---
  const [giftCardCode, setGiftCardCode] = useState("");
  const [giftCardResult, setGiftCardResult] = useState<GiftCardValidation | null>(null);
  const [giftCardLoading, setGiftCardLoading] = useState(false);

  // --- Tax ---
  const [taxResult, setTaxResult] = useState<TaxCalculation | null>(null);
  const [taxLoading, setTaxLoading] = useState(false);

  // --- Checkout ---
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if cart is empty
  useEffect(() => {
    if (items.length === 0) {
      router.replace("/cart");
    }
  }, [items.length, router]);

  // --- Computed totals ---
  const subtotal = cartTotal;
  const discountAmount = discountResult?.valid
    ? Number(discountResult.discount_amount)
    : 0;
  const discountedSubtotal = Math.max(subtotal - discountAmount, 0);
  const taxAmount = taxResult ? Number(taxResult.tax_amount) : 0;
  const giftCardAmount =
    giftCardResult?.valid && giftCardResult.balance
      ? Math.min(Number(giftCardResult.balance), discountedSubtotal + taxAmount)
      : 0;
  const total = Math.max(discountedSubtotal + taxAmount - giftCardAmount, 0);

  // --- Tax calculation on address change ---
  const calculateTax = useCallback(async () => {
    if (!store || !address.country || discountedSubtotal <= 0) {
      setTaxResult(null);
      return;
    }

    setTaxLoading(true);
    const { data } = await api.post<TaxCalculation>(
      `/api/v1/public/stores/${encodeURIComponent(store.slug)}/checkout/calculate-tax`,
      {
        subtotal: discountedSubtotal.toFixed(2),
        country: address.country,
        state: address.state || null,
        postal_code: address.postal_code || null,
      }
    );
    if (data) setTaxResult(data);
    setTaxLoading(false);
  }, [store, address.country, address.state, address.postal_code, discountedSubtotal]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (address.country) calculateTax();
    }, 500);
    return () => clearTimeout(timer);
  }, [calculateTax, address.country]);

  // --- Handlers ---
  async function handleApplyDiscount() {
    if (!store || !discountCode.trim()) return;
    setDiscountLoading(true);
    setDiscountResult(null);

    const productIds = items.map((i) => i.productId);
    const { data, error: apiError } = await api.post<DiscountValidation>(
      `/api/v1/public/stores/${encodeURIComponent(store.slug)}/checkout/validate-discount`,
      {
        code: discountCode.trim(),
        subtotal: subtotal.toFixed(2),
        product_ids: productIds,
      }
    );

    if (apiError) {
      setDiscountResult({
        valid: false,
        discount_type: null,
        value: null,
        discount_amount: "0",
        message: apiError.message || "Could not validate discount.",
      });
    } else if (data) {
      setDiscountResult(data);
    }
    setDiscountLoading(false);
  }

  async function handleApplyGiftCard() {
    if (!store || !giftCardCode.trim()) return;
    setGiftCardLoading(true);
    setGiftCardResult(null);

    const { data, error: apiError } = await api.post<GiftCardValidation>(
      `/api/v1/public/stores/${encodeURIComponent(store.slug)}/gift-cards/validate`,
      { code: giftCardCode.trim() }
    );

    if (apiError) {
      setGiftCardResult({
        valid: false,
        balance: null,
        message: apiError.message || "Could not validate gift card.",
      });
    } else if (data) {
      setGiftCardResult(data);
    }
    setGiftCardLoading(false);
  }

  function isFormValid(): boolean {
    return !!(
      email &&
      email.includes("@") &&
      address.name &&
      address.line1 &&
      address.city &&
      address.postal_code &&
      address.country
    );
  }

  async function handleSubmitCheckout() {
    if (!store || !isFormValid()) return;

    setSubmitting(true);
    setError(null);

    const checkoutItems = items.map((item) => ({
      product_id: item.productId,
      variant_id: item.variantId || undefined,
      quantity: item.quantity,
    }));

    const shippingAddress: ShippingAddress = {
      name: address.name,
      line1: address.line1,
      line2: address.line2 || undefined,
      city: address.city,
      state: address.state || undefined,
      postal_code: address.postal_code,
      country: address.country,
      phone: address.phone || undefined,
    };

    const { data, error: apiError } = await api.post<CheckoutResponse>(
      `/api/v1/public/stores/${encodeURIComponent(store.slug)}/checkout`,
      {
        customer_email: email,
        items: checkoutItems,
        shipping_address: shippingAddress,
        discount_code: discountResult?.valid ? discountCode.trim() : undefined,
        gift_card_code: giftCardResult?.valid ? giftCardCode.trim() : undefined,
      }
    );

    if (apiError) {
      setError(apiError.message || "Checkout failed. Please try again.");
      setSubmitting(false);
      return;
    }

    if (data?.checkout_url) {
      clearCart();
      window.location.href = data.checkout_url;
    }
  }

  if (items.length === 0) return null;

  return (
    <div className="py-10">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="mb-8 text-sm text-theme-muted">
          <Link href="/cart" className="hover:text-theme-primary transition-colors">
            Cart
          </Link>
          <span className="mx-2">/</span>
          <span className="font-medium text-theme-text">Checkout</span>
        </nav>

        <h1 className="text-3xl font-heading font-bold tracking-tight mb-10">
          Checkout
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-10">
          {/* Left column: forms */}
          <div className="lg:col-span-3 space-y-8">
            {/* Section 1: Contact */}
            <section>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-theme-primary text-white text-xs font-bold">
                  1
                </span>
                Contact
              </h2>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
              />
            </section>

            {/* Section 2: Shipping Address */}
            <section>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-theme-primary text-white text-xs font-bold">
                  2
                </span>
                Shipping Address
              </h2>
              <div className="space-y-3">
                <input
                  type="text"
                  value={address.name}
                  onChange={(e) =>
                    setAddress((a) => ({ ...a, name: e.target.value }))
                  }
                  placeholder="Full name"
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                />
                <input
                  type="text"
                  value={address.line1}
                  onChange={(e) =>
                    setAddress((a) => ({ ...a, line1: e.target.value }))
                  }
                  placeholder="Address line 1"
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                />
                <input
                  type="text"
                  value={address.line2 || ""}
                  onChange={(e) =>
                    setAddress((a) => ({ ...a, line2: e.target.value }))
                  }
                  placeholder="Address line 2 (optional)"
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    value={address.city}
                    onChange={(e) =>
                      setAddress((a) => ({ ...a, city: e.target.value }))
                    }
                    placeholder="City"
                    className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  />
                  <input
                    type="text"
                    value={address.state || ""}
                    onChange={(e) =>
                      setAddress((a) => ({ ...a, state: e.target.value }))
                    }
                    placeholder="State / Province"
                    className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    value={address.postal_code}
                    onChange={(e) =>
                      setAddress((a) => ({
                        ...a,
                        postal_code: e.target.value,
                      }))
                    }
                    placeholder="Postal / ZIP code"
                    className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  />
                  <select
                    value={address.country}
                    onChange={(e) =>
                      setAddress((a) => ({ ...a, country: e.target.value }))
                    }
                    className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  >
                    {COUNTRIES.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <input
                  type="tel"
                  value={address.phone || ""}
                  onChange={(e) =>
                    setAddress((a) => ({ ...a, phone: e.target.value }))
                  }
                  placeholder="Phone (optional)"
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                />
              </div>
            </section>

            {/* Section 3: Discount & Gift Card */}
            <section>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-theme-primary text-white text-xs font-bold">
                  3
                </span>
                Discount & Gift Card
              </h2>

              {/* Discount Code */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1.5">
                  Discount Code
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={discountCode}
                    onChange={(e) => {
                      setDiscountCode(e.target.value);
                      if (discountResult) setDiscountResult(null);
                    }}
                    placeholder="Enter discount code"
                    className="flex-1 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2.5 text-sm uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  />
                  <button
                    onClick={handleApplyDiscount}
                    disabled={discountLoading || !discountCode.trim()}
                    className="shrink-0 rounded-lg border border-zinc-300 dark:border-zinc-700 px-5 py-2.5 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {discountLoading ? "Checking..." : "Apply"}
                  </button>
                </div>
                {discountResult && (
                  <div
                    className={`mt-2 rounded-md px-3 py-2 text-sm ${
                      discountResult.valid
                        ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                        : "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800"
                    }`}
                  >
                    {discountResult.message}
                    {discountResult.valid && (
                      <span className="ml-2 font-medium">
                        &minus;${Number(discountResult.discount_amount).toFixed(2)}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Gift Card Code */}
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Gift Card
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={giftCardCode}
                    onChange={(e) => {
                      setGiftCardCode(e.target.value);
                      if (giftCardResult) setGiftCardResult(null);
                    }}
                    placeholder="Enter gift card code"
                    className="flex-1 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2.5 text-sm uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-theme-primary/40 transition-shadow"
                  />
                  <button
                    onClick={handleApplyGiftCard}
                    disabled={giftCardLoading || !giftCardCode.trim()}
                    className="shrink-0 rounded-lg border border-zinc-300 dark:border-zinc-700 px-5 py-2.5 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {giftCardLoading ? "Checking..." : "Apply"}
                  </button>
                </div>
                {giftCardResult && (
                  <div
                    className={`mt-2 rounded-md px-3 py-2 text-sm ${
                      giftCardResult.valid
                        ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                        : "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800"
                    }`}
                  >
                    <p>{giftCardResult.message}</p>
                    {giftCardResult.valid && giftCardResult.balance && (
                      <p className="mt-1 font-medium">
                        Balance: ${Number(giftCardResult.balance).toFixed(2)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* Right column: Order Summary */}
          <div className="lg:col-span-2">
            <div className="sticky top-24 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 p-6">
              <h2 className="text-lg font-semibold mb-5">Order Summary</h2>

              {/* Line items */}
              <div className="space-y-3 mb-6">
                {items.map((item) => (
                  <div
                    key={`${item.productId}-${item.variantId}`}
                    className="flex items-start gap-3"
                  >
                    <div className="relative shrink-0">
                      {item.image ? (
                        <img
                          src={item.image}
                          alt={item.title}
                          className="h-14 w-14 rounded-md object-cover border border-zinc-200 dark:border-zinc-700"
                        />
                      ) : (
                        <div className="h-14 w-14 rounded-md bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center">
                          <div className="h-6 w-6 rounded-full bg-zinc-300 dark:bg-zinc-600" />
                        </div>
                      )}
                      <span className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-600 dark:bg-zinc-400 text-[10px] font-bold text-white dark:text-zinc-900">
                        {item.quantity}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {item.title}
                      </p>
                      {item.variantName && (
                        <p className="text-xs text-theme-muted">
                          {item.variantName}
                        </p>
                      )}
                    </div>
                    <p className="text-sm font-medium shrink-0">
                      ${(item.price * item.quantity).toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>

              {/* Totals */}
              <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-theme-muted">Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>

                {discountAmount > 0 && (
                  <div className="flex justify-between text-emerald-600 dark:text-emerald-400">
                    <span>Discount ({discountCode})</span>
                    <span>&minus;${discountAmount.toFixed(2)}</span>
                  </div>
                )}

                <div className="flex justify-between">
                  <span className="text-theme-muted">
                    Tax
                    {taxLoading && (
                      <span className="ml-1 text-xs opacity-60">
                        calculating...
                      </span>
                    )}
                  </span>
                  <span>${taxAmount.toFixed(2)}</span>
                </div>

                {giftCardAmount > 0 && (
                  <div className="flex justify-between text-emerald-600 dark:text-emerald-400">
                    <span>Gift Card</span>
                    <span>&minus;${giftCardAmount.toFixed(2)}</span>
                  </div>
                )}

                <div className="border-t border-zinc-200 dark:border-zinc-700 pt-3 mt-3 flex justify-between text-base font-bold">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>

              {/* Error */}
              {error && (
                <p className="mt-4 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-600 dark:text-red-400">
                  {error}
                </p>
              )}

              {/* Submit */}
              <button
                onClick={handleSubmitCheckout}
                disabled={submitting || !isFormValid()}
                className="mt-6 w-full rounded-lg bg-theme-primary px-6 py-3.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="h-4 w-4 animate-spin"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : (
                  `Pay $${total.toFixed(2)}`
                )}
              </button>

              <p className="mt-3 text-center text-xs text-theme-muted">
                Secure payment powered by Stripe
              </p>

              <Link
                href="/cart"
                className="block text-center mt-3 text-sm text-theme-muted hover:text-theme-primary transition-colors"
              >
                &larr; Return to cart
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
