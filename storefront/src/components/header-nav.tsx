/**
 * Header navigation for customer auth state.
 *
 * Client component that shows "Sign In" for guests or "Account" dropdown
 * for logged-in customers. Placed in the store header alongside the cart badge.
 *
 * **For Developers:**
 *   Uses ``useCustomerAuth()`` to read customer state. Renders a simple
 *   link set — no complex dropdown, keeping it lightweight.
 *
 * **For QA Engineers:**
 *   - Guest: shows "Sign In" link pointing to ``/login``.
 *   - Logged in: shows customer name/email and "Account" + "Sign Out" links.
 *   - Loading state shows nothing to avoid layout shift.
 */

"use client";

import Link from "next/link";
import { useCustomerAuth } from "@/contexts/customer-auth-context";

/**
 * Header navigation component displaying customer auth status.
 *
 * @returns Navigation links for sign-in or account management.
 */
export function HeaderNav() {
  const { customer, loading, logout } = useCustomerAuth();

  if (loading) return null;

  if (!customer) {
    return (
      <Link
        href="/login"
        className="text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
      >
        Sign In
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link
        href="/account"
        className="text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
      >
        {customer.first_name || customer.email.split("@")[0]}
      </Link>
      <button
        onClick={logout}
        className="text-sm text-zinc-400 dark:text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
      >
        Sign Out
      </button>
    </div>
  );
}
