/**
 * Theme editor page for customizing a store theme.
 *
 * Provides a three-panel editor: sidebar with color/font/style controls,
 * a block manager for page composition, and a save/activate bar.
 * Changes are persisted via PATCH to the theme API.
 *
 * **For End Users:**
 *   This is where you customize your theme's colors, fonts, and homepage
 *   layout. Use the color pickers to set your brand colors, choose fonts
 *   from the dropdown, and arrange page blocks with the toggles.
 *
 * **For QA Engineers:**
 *   - All changes require clicking "Save" to persist.
 *   - Color pickers accept hex values (e.g. "#0d9488").
 *   - Font dropdowns are populated from the ``/themes/meta/fonts`` endpoint.
 *   - Block enable/disable toggles update the blocks array.
 *   - "Save & Activate" saves and activates in one action.
 *
 * **For Developers:**
 *   Fetches the theme via GET ``/stores/{storeId}/themes/{themeId}``.
 *   Saves via PATCH ``/stores/{storeId}/themes/{themeId}``.
 *   Activates via POST ``/stores/{storeId}/themes/{themeId}/activate``.
 *   Font metadata via GET ``/themes/meta/fonts``.
 *   Block types via GET ``/themes/meta/block-types``.
 *
 * **For Project Managers:**
 *   Implements the theme customizer from Part D of the UI/UX overhaul.
 *   Live preview is rendered inline (not an iframe) for simplicity.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition, FadeIn } from "@/components/motion-wrappers";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ColorPicker } from "@/components/ui/color-picker";
import {
  ArrowLeft,
  Save,
  Zap,
  GripVertical,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

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
  blocks: BlockConfig[];
  logo_url: string | null;
  favicon_url: string | null;
  custom_css: string | null;
  created_at: string;
  updated_at: string;
}

/** Shape of a theme block configuration. */
interface BlockConfig {
  type: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

/** Font metadata from the API. */
interface FontMeta {
  heading_fonts: string[];
  body_fonts: string[];
}

/** Color roles used in the theme. */
const COLOR_ROLES = [
  { key: "primary", label: "Primary" },
  { key: "accent", label: "Accent" },
  { key: "background", label: "Background" },
  { key: "surface", label: "Surface" },
  { key: "text", label: "Text" },
  { key: "muted", label: "Muted" },
  { key: "border", label: "Border" },
];

/** Style option definitions. */
const RADIUS_OPTIONS = ["none", "sm", "md", "lg", "xl", "full"];
const CARD_STYLE_OPTIONS = ["flat", "elevated", "glass"];
const BUTTON_STYLE_OPTIONS = ["square", "rounded", "pill"];

/**
 * Skeleton for the editor while loading.
 *
 * @returns Skeleton placeholders for the theme editor.
 */
function EditorSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-8 w-48" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    </div>
  );
}

/**
 * ThemeEditorPage provides a full customization interface for a single theme.
 *
 * @returns The rendered theme editor with color pickers, font selectors,
 *   style options, block manager, and branding inputs.
 */
export default function ThemeEditorPage() {
  const params = useParams();
  const router = useRouter();
  const { store: contextStore } = useStore();
  const storeId = contextStore!.id;
  const themeId = params.themeId as string;
  const { user, loading: authLoading } = useAuth();

  const [theme, setTheme] = useState<Theme | null>(null);
  const [fonts, setFonts] = useState<FontMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Editable state (split out from theme for immediate UI updates)
  const [colors, setColors] = useState<Record<string, string>>({});
  const [typography, setTypography] = useState<Record<string, string>>({});
  const [styles, setStyles] = useState<Record<string, string>>({});
  const [blocks, setBlocks] = useState<BlockConfig[]>([]);
  const [logoUrl, setLogoUrl] = useState("");
  const [faviconUrl, setFaviconUrl] = useState("");
  const [customCss, setCustomCss] = useState("");
  const [themeName, setThemeName] = useState("");

  useEffect(() => {
    if (authLoading || !user) return;

    /**
     * Load the theme data and font metadata in parallel.
     */
    async function load() {
      const [themeRes, fontsRes] = await Promise.all([
        api.get<Theme>(`/api/v1/stores/${storeId}/themes/${themeId}`),
        api.get<FontMeta>("/api/v1/themes/meta/fonts"),
      ]);

      if (themeRes.data) {
        const t = themeRes.data;
        setTheme(t);
        setColors(t.colors || {});
        setTypography(t.typography || {});
        setStyles(t.styles || {});
        setBlocks(t.blocks || []);
        setLogoUrl(t.logo_url || "");
        setFaviconUrl(t.favicon_url || "");
        setCustomCss(t.custom_css || "");
        setThemeName(t.name);
      }

      if (fontsRes.data) {
        setFonts(fontsRes.data);
      }

      setLoading(false);
    }

    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId, themeId, user, authLoading]);

  /**
   * Save the current edits to the backend.
   *
   * @param andActivate - If true, also activate the theme after saving.
   */
  async function handleSave(andActivate = false) {
    setSaving(true);
    setSaveMsg(null);

    const result = await api.patch<Theme>(
      `/api/v1/stores/${storeId}/themes/${themeId}`,
      {
        name: themeName,
        colors,
        typography,
        styles,
        blocks,
        logo_url: logoUrl || null,
        favicon_url: faviconUrl || null,
        custom_css: customCss || null,
      }
    );

    if (result.error) {
      setSaveMsg(`Error: ${result.error.message}`);
      setSaving(false);
      return;
    }

    if (andActivate) {
      await api.post(`/api/v1/stores/${storeId}/themes/${themeId}/activate`, {});
      setSaveMsg("Theme saved and activated!");
    } else {
      setSaveMsg("Theme saved successfully!");
    }

    if (result.data) {
      setTheme(result.data);
    }

    setSaving(false);
    setTimeout(() => setSaveMsg(null), 3000);
  }

  /**
   * Update a single color value.
   *
   * @param key - The color role key (e.g. "primary").
   * @param value - The new hex color value.
   */
  function updateColor(key: string, value: string) {
    setColors((prev) => ({ ...prev, [key]: value }));
  }

  /**
   * Toggle a block's enabled state.
   *
   * @param index - Index of the block in the blocks array.
   */
  function toggleBlock(index: number) {
    setBlocks((prev) =>
      prev.map((b, i) =>
        i === index ? { ...b, enabled: !b.enabled } : b
      )
    );
  }

  /**
   * Move a block up or down in the order.
   *
   * @param index - Current index of the block.
   * @param direction - Direction to move ("up" or "down").
   */
  function moveBlock(index: number, direction: "up" | "down") {
    const newBlocks = [...blocks];
    const target = direction === "up" ? index - 1 : index + 1;
    if (target < 0 || target >= newBlocks.length) return;
    [newBlocks[index], newBlocks[target]] = [newBlocks[target], newBlocks[index]];
    setBlocks(newBlocks);
  }

  if (authLoading || loading) {
    return <EditorSkeleton />;
  }

  if (!theme) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <h2 className="text-xl font-heading font-semibold">Theme not found</h2>
        <Link href={`/stores/${storeId}/themes`}>
          <Button variant="outline">Back to themes</Button>
        </Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        {/* Header */}
        <FadeIn>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link href={`/stores/${storeId}/themes`}>
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-xl font-heading font-semibold">
                  Edit: {themeName}
                </h1>
                <div className="flex items-center gap-2 mt-1">
                  {theme.is_preset && (
                    <Badge variant="secondary">Preset</Badge>
                  )}
                  {theme.is_active && (
                    <Badge variant="success">Active</Badge>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => handleSave(false)}
                disabled={saving}
                className="gap-1"
              >
                <Save className="h-4 w-4" />
                {saving ? "Saving..." : "Save"}
              </Button>
              {!theme.is_active && (
                <Button
                  onClick={() => handleSave(true)}
                  disabled={saving}
                  className="gap-1"
                >
                  <Zap className="h-4 w-4" />
                  Save & Activate
                </Button>
              )}
            </div>
          </div>
        </FadeIn>

        {saveMsg && (
          <Card
            className={
              saveMsg.startsWith("Error")
                ? "border-destructive/50"
                : "border-green-500/50"
            }
          >
            <CardContent className="pt-4 pb-4">
              <p
                className={`text-sm ${
                  saveMsg.startsWith("Error")
                    ? "text-destructive"
                    : "text-green-600"
                }`}
              >
                {saveMsg}
              </p>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left column: Colors + Typography + Styles */}
          <div className="space-y-6">
            {/* Theme Name */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Theme Name
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Input
                  value={themeName}
                  onChange={(e) => setThemeName(e.target.value)}
                  placeholder="Theme name"
                />
              </CardContent>
            </Card>

            {/* Colors */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">Colors</CardTitle>
                <CardDescription>
                  Set the color palette for your storefront
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2">
                  {COLOR_ROLES.map((role) => (
                    <ColorPicker
                      key={role.key}
                      label={role.label}
                      value={colors[role.key] || "#000000"}
                      onChange={(v) => updateColor(role.key, v)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Typography */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Typography
                </CardTitle>
                <CardDescription>
                  Choose fonts for headings and body text
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Heading Font</Label>
                  <select
                    value={typography.heading_font || ""}
                    onChange={(e) =>
                      setTypography((p) => ({
                        ...p,
                        heading_font: e.target.value,
                      }))
                    }
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select a heading font...</option>
                    {fonts?.heading_fonts.map((f: any) => (
                      <option key={typeof f === "string" ? f : f.name} value={typeof f === "string" ? f : f.name}>
                        {typeof f === "string" ? f : f.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Body Font</Label>
                  <select
                    value={typography.body_font || ""}
                    onChange={(e) =>
                      setTypography((p) => ({
                        ...p,
                        body_font: e.target.value,
                      }))
                    }
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select a body font...</option>
                    {fonts?.body_fonts.map((f: any) => (
                      <option key={typeof f === "string" ? f : f.name} value={typeof f === "string" ? f : f.name}>
                        {typeof f === "string" ? f : f.name}
                      </option>
                    ))}
                  </select>
                </div>
              </CardContent>
            </Card>

            {/* Styles */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">Styles</CardTitle>
                <CardDescription>
                  Control border radius, card appearance, and button shape
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Border Radius</Label>
                  <div className="flex gap-2 flex-wrap">
                    {RADIUS_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() =>
                          setStyles((p) => ({ ...p, border_radius: opt }))
                        }
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          styles.border_radius === opt
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border hover:border-muted-foreground/40"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Card Style</Label>
                  <div className="flex gap-2 flex-wrap">
                    {CARD_STYLE_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() =>
                          setStyles((p) => ({ ...p, card_style: opt }))
                        }
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          styles.card_style === opt
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border hover:border-muted-foreground/40"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Button Style</Label>
                  <div className="flex gap-2 flex-wrap">
                    {BUTTON_STYLE_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() =>
                          setStyles((p) => ({ ...p, button_style: opt }))
                        }
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                          styles.button_style === opt
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border hover:border-muted-foreground/40"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right column: Blocks + Branding + Custom CSS */}
          <div className="space-y-6">
            {/* Block Manager */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Page Blocks
                </CardTitle>
                <CardDescription>
                  Enable, disable, and reorder homepage sections
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {blocks.map((block, index) => (
                    <div
                      key={`${block.type}-${index}`}
                      className={`flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors ${
                        block.enabled
                          ? "border-border bg-background"
                          : "border-border/50 bg-muted/30 opacity-60"
                      }`}
                    >
                      <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium capitalize">
                          {block.type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => moveBlock(index, "up")}
                          disabled={index === 0}
                          className="p-1 rounded hover:bg-muted disabled:opacity-30"
                          aria-label="Move up"
                        >
                          <ChevronUp className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          onClick={() => moveBlock(index, "down")}
                          disabled={index === blocks.length - 1}
                          className="p-1 rounded hover:bg-muted disabled:opacity-30"
                          aria-label="Move down"
                        >
                          <ChevronDown className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          onClick={() => toggleBlock(index)}
                          className={`p-1 rounded hover:bg-muted ${
                            block.enabled
                              ? "text-primary"
                              : "text-muted-foreground"
                          }`}
                          aria-label={
                            block.enabled ? "Disable block" : "Enable block"
                          }
                        >
                          {block.enabled ? (
                            <Eye className="h-4 w-4" />
                          ) : (
                            <EyeOff className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                  {blocks.length === 0 && (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                      No blocks configured. Save a preset theme to populate
                      default blocks.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Live Preview */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Color Preview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className="rounded-lg overflow-hidden border border-border"
                  style={{ backgroundColor: colors.background || "#fafaf8" }}
                >
                  {/* Mini header */}
                  <div
                    className="px-4 py-2 border-b flex items-center justify-between"
                    style={{
                      backgroundColor: colors.surface || "#ffffff",
                      borderColor: colors.border || "#e5e5e5",
                    }}
                  >
                    <span
                      className="text-sm font-bold"
                      style={{ color: colors.text || "#1a1a1a" }}
                    >
                      Store Name
                    </span>
                    <div className="flex gap-2">
                      <span
                        className="text-xs"
                        style={{ color: colors.muted || "#6b7280" }}
                      >
                        Products
                      </span>
                      <span
                        className="text-xs"
                        style={{ color: colors.muted || "#6b7280" }}
                      >
                        Categories
                      </span>
                    </div>
                  </div>
                  {/* Mini hero */}
                  <div
                    className="px-4 py-6 text-center"
                    style={{
                      background: `linear-gradient(135deg, ${
                        colors.primary || "#0d9488"
                      }, ${colors.accent || "#d4a853"})`,
                    }}
                  >
                    <span className="text-white text-sm font-bold">
                      Welcome to Your Store
                    </span>
                  </div>
                  {/* Mini product cards */}
                  <div className="p-4 grid grid-cols-3 gap-2">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="rounded p-2"
                        style={{
                          backgroundColor: colors.surface || "#ffffff",
                          border: `1px solid ${colors.border || "#e5e5e5"}`,
                        }}
                      >
                        <div
                          className="h-8 rounded mb-1"
                          style={{
                            backgroundColor: colors.border || "#e5e5e5",
                          }}
                        />
                        <div
                          className="h-2 rounded mb-1 w-3/4"
                          style={{
                            backgroundColor: colors.text || "#1a1a1a",
                            opacity: 0.3,
                          }}
                        />
                        <div
                          className="h-2 rounded w-1/2"
                          style={{
                            backgroundColor: colors.primary || "#0d9488",
                            opacity: 0.6,
                          }}
                        />
                      </div>
                    ))}
                  </div>
                  {/* Mini button */}
                  <div className="px-4 pb-4 text-center">
                    <span
                      className="inline-block px-4 py-1 text-xs rounded"
                      style={{
                        backgroundColor: colors.primary || "#0d9488",
                        color: "#ffffff",
                        borderRadius:
                          styles.button_style === "pill"
                            ? "9999px"
                            : styles.button_style === "square"
                            ? "0"
                            : "0.375rem",
                      }}
                    >
                      Add to Cart
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Branding */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Branding
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="logo-url">Logo URL</Label>
                  <Input
                    id="logo-url"
                    type="url"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                    placeholder="https://example.com/logo.png"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="favicon-url">Favicon URL</Label>
                  <Input
                    id="favicon-url"
                    type="url"
                    value={faviconUrl}
                    onChange={(e) => setFaviconUrl(e.target.value)}
                    placeholder="https://example.com/favicon.ico"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Custom CSS */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading">
                  Custom CSS
                </CardTitle>
                <CardDescription>
                  Advanced: inject custom styles into your storefront
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  id="custom-css"
                  value={customCss}
                  onChange={(e) => setCustomCss(e.target.value)}
                  placeholder=".storefront-header { ... }"
                  rows={6}
                  className="font-mono text-sm"
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
