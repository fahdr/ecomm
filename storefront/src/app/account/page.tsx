/**
 * Customer account dashboard page.
 *
 * **For End Users:**
 *   Your account overview. See recent orders, manage addresses, and
 *   browse your wishlist.
 *
 * **For QA Engineers:**
 *   - Unauthenticated users are redirected to ``/account/login``.
 *   - Shows welcome message with customer name.
 *   - Quick-link cards to orders, wishlist, addresses, and settings.
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";

export default function AccountPage() {
  const { customer, loading, logout } = useCustomerAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !customer) {
      router.replace("/account/login");
    }
  }, [customer, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  if (!customer) return null;

  const displayName = customer.first_name
    ? `${customer.first_name}${customer.last_name ? ` ${customer.last_name}` : ""}`
    : customer.email.split("@")[0];

  const links = [
    { href: "/account/orders", label: "Orders", desc: "View your order history" },
    { href: "/account/wishlist", label: "Wishlist", desc: "Products you've saved" },
    { href: "/account/addresses", label: "Addresses", desc: "Manage shipping addresses" },
    { href: "/account/settings", label: "Settings", desc: "Update your profile" },
  ];

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-heading font-bold">
            Welcome, {displayName}
          </h1>
          <p className="text-sm text-theme-muted">{customer.email}</p>
        </div>
        <button
          onClick={logout}
          className="rounded-lg border border-theme px-3 py-1.5 text-sm text-theme-muted hover:text-red-600 hover:border-red-200 transition-colors"
        >
          Sign Out
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {links.map((link) => (
          <Link key={link.href} href={link.href}>
            <div className="rounded-xl border border-theme bg-theme-surface p-5 transition-all hover:shadow-md hover:-translate-y-0.5">
              <h3 className="font-heading font-semibold">{link.label}</h3>
              <p className="text-sm text-theme-muted mt-1">{link.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
