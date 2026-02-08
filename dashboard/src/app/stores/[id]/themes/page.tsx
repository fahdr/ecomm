/**
 * Storefront theme customization page.
 *
 * Allows store owners to select a storefront theme, set a logo and
 * favicon URL, and inject custom CSS. Changes are persisted via the
 * store PATCH API and take effect immediately on the public storefront.
 *
 * **For End Users:**
 *   Customize the look and feel of your online store. Choose from
 *   pre-built themes, add your brand logo and favicon, or write custom
 *   CSS for fine-grained control.
 *
 * **For QA Engineers:**
 *   - Theme selection updates the ``theme`` field on the store.
 *   - Logo URL and favicon URL are validated as optional strings.
 *   - Custom CSS is stored as-is (no server-side sanitization in MVP).
 *   - Save button calls PATCH ``/api/v1/stores/{id}``.
 *   - Success message auto-dismisses after 3 seconds.
 *
 * **For Developers:**
 *   The Store model has ``theme``, ``logo_url``, ``favicon_url``, and
 *   ``custom_css`` fields (see ``backend/app/models/store.py``). The
 *   storefront reads these fields to apply branding. Theme identifiers
 *   are simple strings; the storefront maps them to CSS class names.
 */

"use client";

import { FormEvent, use, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Available storefront themes. */
const THEMES = [
  {
    id: "default",
    name: "Default",
    description: "Clean, minimal storefront with neutral tones.",
    accent: "bg-slate-800",
  },
  {
    id: "modern",
    name: "Modern",
    description: "Bold typography with high contrast and sharp edges.",
    accent: "bg-zinc-900",
  },
  {
    id: "warm",
    name: "Warm",
    description: "Earthy palette with rounded corners and soft shadows.",
    accent: "bg-amber-700",
  },
  {
    id: "ocean",
    name: "Ocean",
    description: "Cool blue tones with gentle gradients.",
    accent: "bg-sky-600",
  },
  {
    id: "forest",
    name: "Forest",
    description: "Rich greens with natural, organic feel.",
    accent: "bg-emerald-700",
  },
  {
    id: "midnight",
    name: "Midnight",
    description: "Dark theme with purple accents and sleek feel.",
    accent: "bg-violet-800",
  },
];

/** Store data shape returned by the API. */
interface Store {
  id: string;
  name: string;
  theme?: string;
  logo_url?: string | null;
  favicon_url?: string | null;
  custom_css?: string | null;
}

export default function ThemesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Form state
  const [selectedTheme, setSelectedTheme] = useState("default");
  const [logoUrl, setLogoUrl] = useState("");
  const [faviconUrl, setFaviconUrl] = useState("");
  const [customCss, setCustomCss] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    async function fetchStore() {
      const result = await api.get<Store>(`/api/v1/stores/${id}`);
      if (result.error) {
        setNotFound(true);
      } else {
        const s = result.data!;
        setStore(s);
        setSelectedTheme(s.theme || "default");
        setLogoUrl(s.logo_url || "");
        setFaviconUrl(s.favicon_url || "");
        setCustomCss(s.custom_css || "");
      }
      setLoading(false);
    }
    fetchStore();
  }, [id, user, authLoading]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const result = await api.patch<Store>(`/api/v1/stores/${id}`, {
      theme: selectedTheme,
      logo_url: logoUrl || null,
      favicon_url: faviconUrl || null,
      custom_css: customCss || null,
    });

    if (result.error) {
      setSaveError(result.error.message);
      setSaving(false);
      return;
    }

    setStore(result.data!);
    setSaveSuccess(true);
    setSaving(false);
    setTimeout(() => setSaveSuccess(false), 3000);
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-xl font-semibold">Store not found</h2>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            href="/stores"
            className="text-lg font-semibold hover:underline"
          >
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            {store?.name}
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Themes</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-6">
        <form onSubmit={handleSave}>
          {/* Status messages */}
          {saveError && (
            <Card className="mb-4 border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-sm text-destructive">{saveError}</p>
              </CardContent>
            </Card>
          )}
          {saveSuccess && (
            <Card className="mb-4 border-green-500/50">
              <CardContent className="pt-6">
                <p className="text-sm text-green-600">
                  Theme settings saved successfully.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Theme Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Storefront Theme</CardTitle>
              <CardDescription>
                Choose a pre-built theme for your storefront. The selected
                theme controls the overall look, colors, and typography.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {THEMES.map((theme) => (
                  <button
                    key={theme.id}
                    type="button"
                    onClick={() => setSelectedTheme(theme.id)}
                    className={`relative rounded-lg border-2 p-4 text-left transition-all hover:shadow-md ${
                      selectedTheme === theme.id
                        ? "border-primary ring-2 ring-primary/20"
                        : "border-border hover:border-muted-foreground/30"
                    }`}
                  >
                    <div
                      className={`mb-3 h-2 w-full rounded-full ${theme.accent}`}
                    />
                    <h3 className="font-medium">{theme.name}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {theme.description}
                    </p>
                    {selectedTheme === theme.id && (
                      <Badge className="absolute right-2 top-2" variant="default">
                        Active
                      </Badge>
                    )}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Branding */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Branding</CardTitle>
              <CardDescription>
                Add your store&apos;s logo and favicon to reinforce your brand
                on the storefront.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="logo-url">Logo URL</Label>
                <Input
                  id="logo-url"
                  type="url"
                  placeholder="https://example.com/logo.png"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Recommended size: 200x50px. PNG or SVG format.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="favicon-url">Favicon URL</Label>
                <Input
                  id="favicon-url"
                  type="url"
                  placeholder="https://example.com/favicon.ico"
                  value={faviconUrl}
                  onChange={(e) => setFaviconUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Recommended: 32x32px ICO or PNG format.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Custom CSS */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Custom CSS</CardTitle>
              <CardDescription>
                Advanced: inject custom CSS rules into your storefront for
                fine-grained control over styling.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                id="custom-css"
                placeholder={`.storefront-header {\n  background: #1a1a2e;\n}\n\n.product-card {\n  border-radius: 12px;\n}`}
                value={customCss}
                onChange={(e) => setCustomCss(e.target.value)}
                rows={10}
                className="font-mono text-sm"
              />
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Theme Settings"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </main>
    </div>
  );
}
