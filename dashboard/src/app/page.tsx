/**
 * Dashboard home page.
 *
 * The main landing page for authenticated users. Displays a welcome
 * message with the user's email, navigation links, and a logout button.
 *
 * **For End Users:**
 *   This is your dashboard home. Navigate to your stores or log out
 *   using the controls in the header.
 *
 * **For QA Engineers:**
 *   - This page is protected — unauthenticated users are redirected
 *     to `/login` by the middleware.
 *   - A loading spinner shows while the auth state is being resolved.
 *   - The logout button clears tokens and redirects to `/login`.
 *   - The "Stores" link navigates to `/stores`.
 *   - The "Billing" link navigates to `/billing`.
 *   - The "Pricing" link navigates to `/pricing`.
 */

"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";

export default function Home() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">Dropshipping Dashboard</h1>
          <nav className="flex items-center gap-4">
            <Link
              href="/stores"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Stores
            </Link>
            <Link
              href="/billing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Billing
            </Link>
            <Link
              href="/pricing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="flex flex-col items-center gap-6 p-12 text-center">
        <h2 className="text-3xl font-bold tracking-tight">
          Welcome back{user?.email ? `, ${user.email}` : ""}
        </h2>
        <p className="text-lg text-muted-foreground">
          Manage your stores, products, and orders.
        </p>
        <Link href="/stores">
          <Button size="lg">Go to Stores</Button>
        </Link>
      </main>
    </div>
  );
}
