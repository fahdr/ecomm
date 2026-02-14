/**
 * Customer registration page for the storefront.
 *
 * **For End Users:**
 *   Create an account to track orders, save your wishlist, and
 *   speed up checkout with saved addresses.
 *
 * **For QA Engineers:**
 *   - Submit calls ``POST /public/stores/{slug}/customers/register``.
 *   - On success, redirects to ``/account``.
 *   - Duplicate email shows an error message.
 *   - Password must be at least 6 characters.
 */

"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useCustomerAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setSubmitting(true);
    setError(null);
    const err = await register(email, password, firstName, lastName);
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
        Create Account
      </h1>
      <p className="text-theme-muted text-center text-sm mb-8">
        Join us to track orders and save your favorite products.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="firstName" className="block text-sm font-medium mb-1">
              First Name
            </label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
            />
          </div>
          <div>
            <label htmlFor="lastName" className="block text-sm font-medium mb-1">
              Last Name
            </label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
            />
          </div>
        </div>

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
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
          />
        </div>

        <div>
          <label htmlFor="confirm" className="block text-sm font-medium mb-1">
            Confirm Password
          </label>
          <input
            id="confirm"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-theme-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-theme-muted">
        Already have an account?{" "}
        <Link
          href="/account/login"
          className="text-theme-primary hover:underline font-medium"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
