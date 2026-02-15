/**
 * Theme gallery page for store owners.
 *
 * Displays all available themes (presets + custom) for a store. Store
 * owners can activate themes, create custom themes by cloning presets,
 * delete custom themes, and navigate to the full theme editor.
 *
 * **For End Users:**
 *   Browse your store's themes here. Click "Activate" to make a theme
 *   live on your storefront. Click "Customize" to open the theme editor
 *   where you can change colors, fonts, and layout blocks.
 *
 * **For QA Engineers:**
 *   - New stores have 7 preset themes with "Frosted" active by default.
 *   - Only one theme can be active at a time.
 *   - Preset themes cannot be deleted (button should not appear).
 *   - Active themes cannot be deleted (button should be disabled).
 *   - Custom themes can be cloned from any preset via the "Create" dialog.
 *
 * **For Developers:**
 *   Uses the theme API at ``/api/v1/stores/{storeId}/themes``.
 *   Theme activation is via POST ``/themes/{id}/activate``.
 *   Links to ``/stores/{storeId}/themes/{themeId}`` for the editor.
 *
 * **For Project Managers:**
 *   Implements the theme gallery from Part D of the UI/UX overhaul plan.
 *   The theme editor page is a separate route.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition, FadeIn, StaggerChildren, staggerItem } from "@/components/motion-wrappers";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { motion } from "motion/react";
import { Paintbrush, Plus, Trash2, Check, Copy } from "lucide-react";

/** Shape of a theme returned by the API. */
interface Theme {
  id: string;
  store_id: string;
  name: string;
  is_active: boolean;
  is_preset: boolean;
  colors: Record<string, string>;
  typography: Record<string, string>;
  styles: Record<string, string>;
  blocks: Array<Record<string, unknown>>;
  logo_url: string | null;
  favicon_url: string | null;
  custom_css: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Skeleton loader matching the themes gallery layout.
 *
 * @returns Skeleton placeholders for the themes page.
 */
function ThemesSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-9 w-40" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i}>
            <div className="h-24 rounded-t-lg bg-muted" />
            <CardHeader className="pb-2">
              <Skeleton className="h-5 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full mb-2" />
              <div className="flex gap-2">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-8 w-20" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/**
 * ThemesPage renders the theme gallery with activation, creation,
 * and deletion controls.
 *
 * @returns The rendered themes gallery page.
 */
export default function ThemesPage() {
  const { store: contextStore } = useStore();
  const storeId = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [cloneSource, setCloneSource] = useState<string>("");
  const [newName, setNewName] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);

  /**
   * Fetch all themes for this store from the API.
   */
  async function fetchThemes() {
    const result = await api.get<Theme[]>(
      `/api/v1/stores/${storeId}/themes`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setThemes(result.data ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchThemes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId, user, authLoading]);

  /**
   * Activate a theme for this store.
   *
   * @param themeId - UUID of the theme to activate.
   */
  async function handleActivate(themeId: string) {
    setActivating(themeId);
    const result = await api.post<Theme>(
      `/api/v1/stores/${storeId}/themes/${themeId}/activate`,
      {}
    );
    if (!result.error) {
      setThemes((prev) =>
        prev.map((t) => ({
          ...t,
          is_active: t.id === themeId,
        }))
      );
    }
    setActivating(null);
  }

  /**
   * Create a new custom theme, optionally cloning from a preset.
   */
  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    const result = await api.post<Theme>(
      `/api/v1/stores/${storeId}/themes`,
      {
        name: newName.trim(),
        clone_from: cloneSource || null,
      }
    );
    if (!result.error && result.data) {
      setThemes((prev) => [...prev, result.data!]);
      setNewName("");
      setCloneSource("");
      setShowCreateForm(false);
    }
    setCreating(false);
  }

  /**
   * Delete a custom theme.
   *
   * @param themeId - UUID of the theme to delete.
   */
  async function handleDelete(themeId: string) {
    const result = await api.delete(`/api/v1/stores/${storeId}/themes/${themeId}`);
    if (!result.error) {
      setThemes((prev) => prev.filter((t) => t.id !== themeId));
    }
  }

  if (authLoading || loading) {
    return <ThemesSkeleton />;
  }

  const presets = themes.filter((t) => t.is_preset);
  const custom = themes.filter((t) => !t.is_preset);

  return (
    <PageTransition>
      <div className="space-y-8">
        {/* Header */}
        <FadeIn>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold font-heading">Themes</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Choose and customize your storefront&apos;s appearance
              </p>
            </div>
            <Button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Custom Theme
            </Button>
          </div>
        </FadeIn>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Create custom theme form */}
        {showCreateForm && (
          <FadeIn>
            <Card>
              <CardHeader>
                <CardTitle className="font-heading text-lg">
                  Create Custom Theme
                </CardTitle>
                <CardDescription>
                  Start from scratch or clone an existing preset
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Theme Name</label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="My Custom Theme"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Clone From (optional)
                  </label>
                  <select
                    value={cloneSource}
                    onChange={(e) => setCloneSource(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Default (Frosted)</option>
                    {presets.map((p) => (
                      <option key={p.id} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleCreate}
                    disabled={creating || !newName.trim()}
                  >
                    {creating ? "Creating..." : "Create Theme"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Preset Themes */}
        <section>
          <h2 className="text-lg font-medium font-heading mb-4">
            Preset Themes
          </h2>
          <StaggerChildren className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {presets.map((theme) => (
              <ThemeCard
                key={theme.id}
                theme={theme}
                storeId={storeId}
                activating={activating}
                onActivate={handleActivate}
                onDelete={handleDelete}
              />
            ))}
          </StaggerChildren>
        </section>

        {/* Custom Themes */}
        {custom.length > 0 && (
          <section>
            <h2 className="text-lg font-medium font-heading mb-4">
              Custom Themes
            </h2>
            <StaggerChildren className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {custom.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  storeId={storeId}
                  activating={activating}
                  onActivate={handleActivate}
                  onDelete={handleDelete}
                />
              ))}
            </StaggerChildren>
          </section>
        )}
      </div>
    </PageTransition>
  );
}

/**
 * Individual theme card with color swatch preview, activation, and actions.
 *
 * @param props - Component props.
 * @param props.theme - The theme data object.
 * @param props.storeId - The store UUID for generating editor links.
 * @param props.activating - ID of the theme currently being activated (or null).
 * @param props.onActivate - Callback to activate this theme.
 * @param props.onDelete - Callback to delete this theme.
 * @returns A card displaying the theme preview and action buttons.
 */
function ThemeCard({
  theme,
  storeId,
  activating,
  onActivate,
  onDelete,
}: {
  theme: Theme;
  storeId: string;
  activating: string | null;
  onActivate: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const colors = theme.colors || {};

  return (
    <motion.div variants={staggerItem}>
      <Card className="overflow-hidden group">
        {/* Color swatch preview */}
        <div className="h-20 relative flex">
          <div
            className="flex-1"
            style={{ backgroundColor: colors.primary || "#0d9488" }}
          />
          <div
            className="flex-1"
            style={{ backgroundColor: colors.accent || "#d4a853" }}
          />
          <div
            className="flex-1"
            style={{ backgroundColor: colors.background || "#fafaf8" }}
          />
          <div
            className="flex-1"
            style={{ backgroundColor: colors.surface || "#ffffff" }}
          />
          {theme.is_active && (
            <div className="absolute top-2 right-2">
              <Badge variant="success" className="gap-1">
                <Check className="h-3 w-3" />
                Active
              </Badge>
            </div>
          )}
        </div>

        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-heading">
              {theme.name}
            </CardTitle>
            {theme.is_preset && (
              <Badge variant="secondary" className="text-xs">
                Preset
              </Badge>
            )}
          </div>
          <CardDescription className="text-xs">
            {theme.typography?.heading_font || "Default"} /{" "}
            {theme.typography?.body_font || "Default"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="flex gap-2 flex-wrap">
            {!theme.is_active && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onActivate(theme.id)}
                disabled={activating === theme.id}
                className="gap-1"
              >
                <Check className="h-3 w-3" />
                {activating === theme.id ? "Activating..." : "Activate"}
              </Button>
            )}
            <Link href={`/stores/${storeId}/themes/${theme.id}`}>
              <Button size="sm" variant="outline" className="gap-1">
                <Paintbrush className="h-3 w-3" />
                Customize
              </Button>
            </Link>
            {!theme.is_preset && !theme.is_active && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onDelete(theme.id)}
                className="gap-1 text-destructive hover:text-destructive"
              >
                <Trash2 className="h-3 w-3" />
                Delete
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
