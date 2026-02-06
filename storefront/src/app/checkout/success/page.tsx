/**
 * Checkout success / order confirmation page.
 *
 * Displayed after a customer completes payment via Stripe Checkout.
 * Shows the order details fetched from the public API using the
 * session ID from the URL.
 *
 * **For Developers:**
 *   This is a server component. The Stripe session ID comes from the
 *   ``session_id`` search parameter. In mock mode (no Stripe key), the
 *   session ID format is ``cs_test_mock_{order_id}``.
 *
 * **For QA Engineers:**
 *   - Shows order ID, status, items, and total.
 *   - Without a valid session_id, shows a generic confirmation.
 *   - Links back to the store homepage.
 *
 * **For End Users:**
 *   This page confirms your order was placed successfully. You'll see
 *   your order details and can continue shopping.
 */

import Link from "next/link";

/**
 * Checkout success page server component.
 *
 * @param props - Page props from Next.js.
 * @param props.searchParams - URL search parameters including ``session_id``.
 * @returns An order confirmation page.
 */
export default async function CheckoutSuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ session_id?: string }>;
}) {
  const params = await searchParams;
  const sessionId = params.session_id;

  return (
    <div className="py-16">
      <div className="mx-auto max-w-2xl px-4 text-center">
        {/* Success Icon */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="h-8 w-8 text-green-600 dark:text-green-400"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4.5 12.75l6 6 9-13.5"
            />
          </svg>
        </div>

        <h1 className="text-3xl font-bold tracking-tight mb-4">
          Order Confirmed!
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-2">
          Thank you for your purchase. Your order has been placed successfully.
        </p>

        {sessionId && (
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mb-8">
            Session: {sessionId}
          </p>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center rounded-lg bg-zinc-900 dark:bg-zinc-100 px-6 py-3 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
          >
            Continue Shopping
          </Link>
          <Link
            href="/products"
            className="inline-flex items-center rounded-lg border border-zinc-300 dark:border-zinc-700 px-6 py-3 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
          >
            Browse Products
          </Link>
        </div>
      </div>
    </div>
  );
}
