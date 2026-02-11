/**
 * Account link component for the storefront header.
 *
 * Shows a user icon linking to the account dashboard when logged in,
 * or a "Sign In" link when not authenticated.
 *
 * **For Developers:**
 *   This is a client component because it consumes ``useCustomerAuth()``
 *   to read authentication state. It's rendered inside the server-side
 *   ``StoreHeader`` in ``layout.tsx``.
 *
 * **For QA Engineers:**
 *   - When logged out: shows "Sign In" text link to ``/account/login``.
 *   - When logged in: shows a user icon linking to ``/account``.
 *   - Loading state: renders nothing to prevent layout shift.
 */

"use client";

import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";

/**
 * Renders the account link in the storefront header.
 *
 * @returns A link element for account access, or null while loading.
 */
export function AccountLink() {
  const { customer, loading } = useCustomerAuth();

  if (loading) return null;

  if (customer) {
    return (
      <Link
        href="/account"
        className="text-sm text-theme-muted hover:text-theme-primary transition-colors"
        title="My Account"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </Link>
    );
  }

  return (
    <Link
      href="/account/login"
      className="text-sm text-theme-muted hover:text-theme-primary transition-colors"
    >
      Sign In
    </Link>
  );
}
