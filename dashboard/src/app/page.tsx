/**
 * Dashboard home page.
 *
 * The main landing page for authenticated users. Displays a welcome
 * message with quick links and the user's store count.
 *
 * **For End Users:**
 *   This is your dashboard home. Navigate to your stores from here.
 *
 * **For QA Engineers:**
 *   - Protected page — unauthenticated users redirect to /login
 *   - Loading state shows spinner while auth resolves
 *   - "Go to Stores" navigates to /stores
 */

"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { FadeIn } from "@/components/motion-wrappers";
import {
  Store,
  CreditCard,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-dot-pattern">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dot-pattern">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-3">
        <h1 className="font-heading text-lg font-semibold">Dropshipping Dashboard</h1>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <FadeIn>
          <div className="space-y-2 mb-10">
            <h2 className="font-heading text-3xl font-bold tracking-tight">
              Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}
            </h2>
            <p className="text-lg text-muted-foreground">
              Manage your stores, products, and orders.
            </p>
          </div>
        </FadeIn>

        <FadeIn delay={0.1}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Link href="/stores" className="group">
              <div className="flex items-center gap-4 rounded-xl border bg-card/80 backdrop-blur-sm p-5 transition-all hover:shadow-md hover:-translate-y-0.5">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Store className="size-5" />
                </div>
                <div className="flex-1">
                  <h3 className="font-heading font-semibold">Your Stores</h3>
                  <p className="text-sm text-muted-foreground">Manage products & orders</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
            <Link href="/billing" className="group">
              <div className="flex items-center gap-4 rounded-xl border bg-card/80 backdrop-blur-sm p-5 transition-all hover:shadow-md hover:-translate-y-0.5">
                <div className="flex size-10 items-center justify-center rounded-lg bg-accent/20 text-accent-foreground">
                  <CreditCard className="size-5" />
                </div>
                <div className="flex-1">
                  <h3 className="font-heading font-semibold">Billing</h3>
                  <p className="text-sm text-muted-foreground">Plans & subscription</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          </div>
        </FadeIn>
      </main>
    </div>
  );
}
