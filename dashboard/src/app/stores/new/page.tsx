/**
 * Create Store page.
 *
 * Provides a form for creating a new dropshipping store with a name,
 * niche category picker, and optional description. On success, redirects
 * to the new store's settings page.
 *
 * **For End Users:**
 *   Fill in your store name, choose a niche from the dropdown, and
 *   optionally add a description. Click "Create Store" to set it up.
 *   A unique URL slug will be generated automatically from the name.
 *
 * **For QA Engineers:**
 *   - The name field is required.
 *   - The niche field is required (dropdown selection).
 *   - The description is optional.
 *   - The submit button is disabled while the request is in flight.
 *   - Backend validation errors (if any) are displayed below the form.
 *   - On success, redirects to `/stores/{id}`.
 *
 * **For Developers:**
 *   - Uses `bg-dot-pattern` background for visual consistency with the overhaul.
 *   - Header uses backdrop blur and `font-heading` for titles.
 *   - Main content wrapped in `PageTransition` for entrance animation.
 *   - ThemeToggle is present in the header for dark/light mode switching.
 *
 * **For Project Managers:**
 *   This page is part of the store creation flow. It is NOT store-scoped
 *   (no sidebar), and uses its own top bar with breadcrumbs.
 */

"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageTransition } from "@/components/motion-wrappers";
import { ThemeToggle } from "@/components/theme-toggle";

/** Predefined niche categories for the store. */
const NICHES = [
  "Electronics",
  "Fashion",
  "Home & Garden",
  "Health & Beauty",
  "Sports & Outdoors",
  "Toys & Games",
  "Pet Supplies",
  "Automotive",
  "Office Supplies",
  "Food & Beverages",
  "Other",
];

/** Store data returned by the create API. */
interface StoreResponse {
  id: string;
  name: string;
  slug: string;
  niche: string;
}

/**
 * CreateStorePage renders a form for creating a new dropshipping store.
 *
 * Handles form state, validation, API submission, and redirect on success.
 *
 * @returns The rendered create-store page with header and form card.
 */
export default function CreateStorePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [niche, setNiche] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle form submission -- call the stores API to create a new store.
   *
   * Validates that a niche is selected, then posts to the backend.
   * On success, redirects to the newly created store's page.
   *
   * @param e - The form submit event.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!niche) {
      setError("Please select a niche.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const result = await api.post<StoreResponse>("/api/v1/stores", {
      name,
      niche,
      description: description || null,
    });

    if (result.error) {
      setError(result.error.message);
      setSubmitting(false);
      return;
    }

    router.push(`/stores/${result.data!.id}`);
  }

  return (
    <div className="min-h-screen bg-dot-pattern">
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-heading font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-heading font-semibold">Create Store</h1>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex justify-center p-6">
        <PageTransition>
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle className="font-heading">Create a new store</CardTitle>
              <CardDescription>
                Set up your dropshipping store. A unique URL will be generated
                from the store name.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4">
                {error && (
                  <p className="text-sm text-destructive text-center">{error}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="name">Store Name</Label>
                  <Input
                    id="name"
                    placeholder="My Awesome Store"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="niche">Niche</Label>
                  <Select value={niche} onValueChange={setNiche}>
                    <SelectTrigger id="niche">
                      <SelectValue placeholder="Select a niche" />
                    </SelectTrigger>
                    <SelectContent>
                      {NICHES.map((n) => (
                        <SelectItem key={n} value={n.toLowerCase()}>
                          {n}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="Tell customers what your store is about..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end gap-2">
                <Link href="/stores">
                  <Button type="button" variant="outline">
                    Cancel
                  </Button>
                </Link>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Creating..." : "Create Store"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </PageTransition>
      </main>
    </div>
  );
}
