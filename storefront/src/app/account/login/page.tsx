/**
 * Customer login page for the storefront.
 *
 * **For End Users:**
 *   Sign in to your account to view orders, manage your wishlist,
 *   and speed up checkout with saved addresses.
 *
 * **For QA Engineers:**
 *   - Submit calls ``POST /public/stores/{slug}/customers/login``.
 *   - On success, redirects to ``/account``.
 *   - Invalid credentials show an error message.
 *   - Links to ``/account/register`` for new accounts.
 */

"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useCustomerAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const err = await login(email, password);
    if (err) {
      setError(err);
      setSubmitting(false);
    } else {
      router.push("/account");
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-heading font-bold text-center mb-2">
        Sign In
      </h1>
      <p className="text-theme-muted text-center text-sm mb-8">
        Sign in to your account to view orders and manage your wishlist.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-theme-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-theme-muted">
        Don&apos;t have an account?{" "}
        <Link
          href="/account/register"
          className="text-theme-primary hover:underline font-medium"
        >
          Create one
        </Link>
      </p>
    </div>
  );
}
