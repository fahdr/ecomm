/**
 * Customer account overview page.
 *
 * Shows the customer's profile with links to order history and wishlist.
 * Redirects to ``/login`` if the customer is not authenticated.
 *
 * **For Developers:**
 *   Client component using ``useCustomerAuth()`` for customer state.
 *   Includes inline profile editing for name and phone.
 *
 * **For QA Engineers:**
 *   - Unauthenticated users are redirected to ``/login``.
 *   - Profile fields can be updated inline.
 *   - Links to Orders and Wishlist sub-pages.
 *   - Sign Out button clears tokens and redirects to ``/``.
 *
 * **For End Users:**
 *   Manage your account details, view your order history, and access
 *   your saved wishlist items.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/customer-auth-context";

/**
 * Account overview page component.
 *
 * @returns The customer account page with profile and navigation.
 */
export default function AccountPage() {
  const { customer, loading, logout, updateProfile, error } = useCustomerAuth();
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!loading && !customer) {
      router.replace("/login");
    }
  }, [loading, customer, router]);

  useEffect(() => {
    if (customer) {
      setFirstName(customer.first_name || "");
      setLastName(customer.last_name || "");
      setPhone(customer.phone || "");
    }
  }, [customer]);

  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    const success = await updateProfile({
      first_name: firstName || undefined,
      last_name: lastName || undefined,
      phone: phone || undefined,
    });
    if (success) {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
    setSaving(false);
  }

  function handleLogout() {
    logout();
    router.push("/");
  }

  if (loading || !customer) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold tracking-tight mb-8">My Account</h2>

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <Link
            href="/account/orders"
            className="flex flex-col items-center gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-8 w-8 text-zinc-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 10.5V6a3.75 3.75 0 1 0-7.5 0v4.5m11.356-1.993 1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 0 1-1.12-1.243l1.264-12A1.125 1.125 0 0 1 5.513 7.5h12.974c.576 0 1.059.435 1.119 1.007ZM8.625 10.5a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm7.5 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
              />
            </svg>
            <span className="text-sm font-medium">Order History</span>
          </Link>
          <Link
            href="/account/wishlist"
            className="flex flex-col items-center gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-8 w-8 text-zinc-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z"
              />
            </svg>
            <span className="text-sm font-medium">Wishlist</span>
          </Link>
        </div>

        {/* Profile Form */}
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Profile</h3>

          <form onSubmit={handleUpdate} className="space-y-4">
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
            {saved && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Profile updated successfully.
              </p>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Email
              </label>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {customer.email}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label
                  htmlFor="prof-first"
                  className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
                >
                  First Name
                </label>
                <input
                  id="prof-first"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                />
              </div>
              <div>
                <label
                  htmlFor="prof-last"
                  className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
                >
                  Last Name
                </label>
                <input
                  id="prof-last"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="prof-phone"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
              >
                Phone
              </label>
              <input
                id="prof-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                placeholder="+1 (555) 123-4567"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-zinc-900 dark:bg-zinc-100 px-5 py-2 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50"
              >
                {saving ? "Saving..." : "Update Profile"}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="text-sm text-zinc-500 hover:text-red-500 transition-colors"
              >
                Sign Out
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
