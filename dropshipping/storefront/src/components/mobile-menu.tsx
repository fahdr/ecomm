/**
 * Mobile slide-out navigation menu for the storefront.
 *
 * Renders a hamburger button (visible below `sm` breakpoint) that opens
 * a slide-out drawer with navigation links, account access, and close
 * controls.
 *
 * **For Developers:**
 *   Client component using CSS transforms for the slide animation.
 *   Closes on: nav link click, outside click (backdrop), Escape key.
 *   Uses ``useCustomerAuth()`` for conditional account/sign-in link.
 *
 * **For QA Engineers:**
 *   - Hamburger icon only visible on mobile (below sm breakpoint).
 *   - Drawer slides in from left with backdrop overlay.
 *   - All nav links navigate and close the drawer.
 *   - Escape key closes the drawer.
 *   - Backdrop click closes the drawer.
 *
 * **For End Users:**
 *   Tap the menu icon on mobile to access navigation links.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";

/**
 * Props for the MobileMenu component.
 *
 * @param storeName - The store's display name shown at the top of the drawer.
 */
interface MobileMenuProps {
  storeName: string;
}

/**
 * Mobile navigation drawer with hamburger trigger.
 *
 * @param props - Component props.
 * @returns A hamburger button and slide-out navigation drawer.
 */
export function MobileMenu({ storeName }: MobileMenuProps) {
  const [open, setOpen] = useState(false);
  const { customer } = useCustomerAuth();

  useEffect(() => {
    if (!open) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open]);

  function close() {
    setOpen(false);
  }

  return (
    <>
      {/* Hamburger button — visible only on mobile */}
      <button
        onClick={() => setOpen(true)}
        className="sm:hidden inline-flex items-center justify-center text-theme-muted hover:text-theme-primary transition-colors"
        aria-label="Open menu"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="4" x2="20" y1="12" y2="12" />
          <line x1="4" x2="20" y1="6" y2="6" />
          <line x1="4" x2="20" y1="18" y2="18" />
        </svg>
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity"
          onClick={close}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-theme-surface border-r border-theme shadow-xl transform transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-16 border-b border-theme">
          <span className="text-lg font-heading font-bold tracking-tight">
            {storeName}
          </span>
          <button
            onClick={close}
            className="text-theme-muted hover:text-theme-primary transition-colors"
            aria-label="Close menu"
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
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex flex-col px-5 py-4 gap-1">
          <Link
            href="/products"
            onClick={close}
            className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
          >
            Products
          </Link>
          <Link
            href="/categories"
            onClick={close}
            className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
          >
            Categories
          </Link>
          <Link
            href="/search"
            onClick={close}
            className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
          >
            Search
          </Link>

          <div className="border-t border-theme my-3" />

          {customer ? (
            <>
              <Link
                href="/account"
                onClick={close}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
              >
                My Account
              </Link>
              <Link
                href="/account/orders"
                onClick={close}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
              >
                Orders
              </Link>
              <Link
                href="/account/wishlist"
                onClick={close}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
              >
                Wishlist
              </Link>
            </>
          ) : (
            <Link
              href="/account/login"
              onClick={close}
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-primary hover:bg-theme-surface transition-colors"
            >
              Sign In
            </Link>
          )}

          <div className="border-t border-theme my-3" />

          <Link
            href="/cart"
            onClick={close}
            className="rounded-lg px-3 py-2.5 text-sm font-medium text-theme-muted hover:text-theme-primary hover:bg-theme-surface transition-colors"
          >
            Cart
          </Link>
        </nav>
      </div>
    </>
  );
}
