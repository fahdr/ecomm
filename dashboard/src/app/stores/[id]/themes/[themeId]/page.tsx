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
import { Switch } from "@/components/ui/switch";
import {
  ArrowLeft,
  Save,
  Zap,
  GripVertical,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  Settings2,
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

// ── Block Config Editor ─────────────────────────────────────────────────
// Renders per-block-type configuration forms inside the expandable panels.

/** Props for the block config editor. */
interface BlockConfigEditorProps {
  block: BlockConfig;
  index: number;
  onUpdate: (index: number, key: string, value: unknown) => void;
}

/** A reusable text input row for block config. */
function ConfigInput({ label, value, onChange, placeholder, type = "text" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="h-8 text-xs" />
    </div>
  );
}

/** A reusable select row for block config. */
function ConfigSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

/** A reusable number input row for block config. */
function ConfigNumber({ label, value, onChange, min, max }: {
  label: string; value: number; onChange: (v: number) => void; min?: number; max?: number;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        className="h-8 text-xs w-24"
      />
    </div>
  );
}

/** A reusable toggle row for block config. */
function ConfigToggle({ label, value, onChange }: {
  label: string; value: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <Label className="text-xs">{label}</Label>
      <Switch checked={value} onCheckedChange={onChange} />
    </div>
  );
}

/**
 * Renders the appropriate config form for a block type.
 *
 * @param props - Block, index, and update callback.
 * @returns Config form fields specific to the block type.
 */
function BlockConfigEditor({ block, index, onUpdate }: BlockConfigEditorProps) {
  const c = block.config;
  const upd = (key: string, value: unknown) => onUpdate(index, key, value);

  switch (block.type) {
    case "hero_banner":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigInput label="Subtitle" value={(c.subtitle as string) || ""} onChange={(v) => upd("subtitle", v)} />
          <ConfigInput label="CTA Text" value={(c.cta_text as string) || ""} onChange={(v) => upd("cta_text", v)} />
          <ConfigInput label="CTA Link" value={(c.cta_link as string) || ""} onChange={(v) => upd("cta_link", v)} />
          <ConfigSelect label="Background" value={(c.bg_type as string) || "gradient"} onChange={(v) => upd("bg_type", v)} options={[
            { value: "gradient", label: "Gradient" }, { value: "solid", label: "Solid Color" },
            { value: "image", label: "Image" }, { value: "product_showcase", label: "Product Showcase" },
          ]} />
          {(c.bg_type === "image") && (
            <ConfigInput label="Background Image URL" value={(c.bg_image as string) || ""} onChange={(v) => upd("bg_image", v)} placeholder="https://..." />
          )}
          <ConfigSelect label="Text Position" value={(c.text_position as string) || "center"} onChange={(v) => upd("text_position", v)} options={[
            { value: "left", label: "Left" }, { value: "center", label: "Center" }, { value: "right", label: "Right" },
          ]} />
          <ConfigSelect label="Height" value={(c.height as string) || "lg"} onChange={(v) => upd("height", v)} options={[
            { value: "sm", label: "Small" }, { value: "md", label: "Medium" }, { value: "lg", label: "Large" }, { value: "full", label: "Full Screen" },
          ]} />
          <ConfigSelect label="Overlay Style" value={(c.overlay_style as string) || "gradient"} onChange={(v) => upd("overlay_style", v)} options={[
            { value: "gradient", label: "Gradient" }, { value: "blur", label: "Blur" }, { value: "dark", label: "Dark" }, { value: "none", label: "None" },
          ]} />
        </div>
      );

    case "featured_products":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <div className="flex gap-4">
            <ConfigNumber label="Count" value={typeof c.count === "number" ? c.count : 8} onChange={(v) => upd("count", v)} min={2} max={24} />
            <ConfigNumber label="Columns" value={typeof c.columns === "number" ? c.columns : 4} onChange={(v) => upd("columns", v)} min={2} max={6} />
          </div>
          <ConfigToggle label="Show Prices" value={c.show_prices !== false} onChange={(v) => upd("show_prices", v)} />
          <ConfigToggle label="Show Badges" value={c.show_badges !== false} onChange={(v) => upd("show_badges", v)} />
        </div>
      );

    case "categories_grid":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigNumber label="Columns" value={typeof c.columns === "number" ? c.columns : 3} onChange={(v) => upd("columns", v)} min={2} max={5} />
          <ConfigToggle label="Show Product Count" value={c.show_product_count !== false} onChange={(v) => upd("show_product_count", v)} />
        </div>
      );

    case "product_carousel":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigNumber label="Product Count" value={typeof c.count === "number" ? c.count : 10} onChange={(v) => upd("count", v)} min={4} max={20} />
          <ConfigToggle label="Auto Scroll" value={c.auto_scroll === true} onChange={(v) => upd("auto_scroll", v)} />
          {c.auto_scroll === true && (
            <ConfigNumber label="Interval (ms)" value={typeof c.interval === "number" ? c.interval : 4000} onChange={(v) => upd("interval", v)} min={2000} max={10000} />
          )}
          <ConfigToggle label="Show Prices" value={c.show_prices !== false} onChange={(v) => upd("show_prices", v)} />
        </div>
      );

    case "reviews":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigNumber label="Count" value={typeof c.count === "number" ? c.count : 6} onChange={(v) => upd("count", v)} min={3} max={12} />
          <ConfigSelect label="Layout" value={(c.layout as string) || "grid"} onChange={(v) => upd("layout", v)} options={[
            { value: "grid", label: "Grid" }, { value: "slider", label: "Slider" },
          ]} />
        </div>
      );

    case "newsletter":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigInput label="Subtitle" value={(c.subtitle as string) || ""} onChange={(v) => upd("subtitle", v)} />
          <ConfigInput label="Button Text" value={(c.button_text as string) || ""} onChange={(v) => upd("button_text", v)} />
        </div>
      );

    case "testimonials":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigSelect label="Layout" value={(c.layout as string) || "cards"} onChange={(v) => upd("layout", v)} options={[
            { value: "cards", label: "Card Grid" }, { value: "slider", label: "Slider" },
          ]} />
          <div>
            <Label className="text-xs mb-2 block">Testimonials</Label>
            {Array.isArray(c.items) && (c.items as Array<Record<string, string>>).map((item, i) => (
              <div key={i} className="border border-border rounded-md p-2 mb-2 space-y-1">
                <Input
                  value={item.quote || ""}
                  onChange={(e) => {
                    const items = [...(c.items as Array<Record<string, string>>)];
                    items[i] = { ...items[i], quote: e.target.value };
                    upd("items", items);
                  }}
                  placeholder="Quote text"
                  className="h-7 text-xs"
                />
                <div className="flex gap-2">
                  <Input
                    value={item.author || ""}
                    onChange={(e) => {
                      const items = [...(c.items as Array<Record<string, string>>)];
                      items[i] = { ...items[i], author: e.target.value };
                      upd("items", items);
                    }}
                    placeholder="Author"
                    className="h-7 text-xs flex-1"
                  />
                  <Input
                    value={item.role || ""}
                    onChange={(e) => {
                      const items = [...(c.items as Array<Record<string, string>>)];
                      items[i] = { ...items[i], role: e.target.value };
                      upd("items", items);
                    }}
                    placeholder="Role"
                    className="h-7 text-xs flex-1"
                  />
                </div>
                <button type="button" onClick={() => {
                  const items = (c.items as Array<Record<string, string>>).filter((_, j) => j !== i);
                  upd("items", items);
                }} className="text-xs text-destructive hover:underline">Remove</button>
              </div>
            ))}
            <button type="button" onClick={() => {
              const items = [...(Array.isArray(c.items) ? c.items : []), { quote: "", author: "", role: "" }];
              upd("items", items);
            }} className="text-xs text-primary hover:underline flex items-center gap-1">
              <Plus className="h-3 w-3" /> Add Testimonial
            </button>
          </div>
        </div>
      );

    case "countdown_timer":
      return (
        <div className="space-y-3">
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigInput label="Subtitle" value={(c.subtitle as string) || ""} onChange={(v) => upd("subtitle", v)} />
          <ConfigInput label="Target Date" value={(c.target_date as string) || ""} onChange={(v) => upd("target_date", v)} type="datetime-local" />
          <ConfigInput label="CTA Text" value={(c.cta_text as string) || ""} onChange={(v) => upd("cta_text", v)} />
          <ConfigInput label="CTA Link" value={(c.cta_link as string) || ""} onChange={(v) => upd("cta_link", v)} />
          <ConfigSelect label="Background" value={(c.bg_style as string) || "gradient"} onChange={(v) => upd("bg_style", v)} options={[
            { value: "gradient", label: "Gradient" }, { value: "solid", label: "Solid" }, { value: "transparent", label: "Transparent" },
          ]} />
        </div>
      );

    case "video_banner":
      return (
        <div className="space-y-3">
          <ConfigInput label="Video URL" value={(c.video_url as string) || ""} onChange={(v) => upd("video_url", v)} placeholder="YouTube, Vimeo, or .mp4 URL" />
          <ConfigInput label="Poster Image URL" value={(c.poster_url as string) || ""} onChange={(v) => upd("poster_url", v)} />
          <ConfigInput label="Overlay Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigInput label="Overlay Subtitle" value={(c.subtitle as string) || ""} onChange={(v) => upd("subtitle", v)} />
          <ConfigToggle label="Autoplay (muted)" value={c.autoplay === true} onChange={(v) => upd("autoplay", v)} />
        </div>
      );

    case "trust_badges":
      return (
        <div className="space-y-3">
          <ConfigNumber label="Columns" value={typeof c.columns === "number" ? c.columns : 4} onChange={(v) => upd("columns", v)} min={2} max={6} />
          <div>
            <Label className="text-xs mb-2 block">Badges</Label>
            {Array.isArray(c.badges) && (c.badges as Array<Record<string, string>>).map((badge, i) => (
              <div key={i} className="border border-border rounded-md p-2 mb-2 space-y-1">
                <div className="flex gap-2">
                  <select
                    value={badge.icon || "check-circle"}
                    onChange={(e) => {
                      const badges = [...(c.badges as Array<Record<string, string>>)];
                      badges[i] = { ...badges[i], icon: e.target.value };
                      upd("badges", badges);
                    }}
                    className="rounded border border-border bg-background px-2 py-1 text-xs w-32"
                  >
                    {["truck", "shield", "rotate-ccw", "headphones", "clock", "award", "lock", "heart", "star", "zap", "check-circle", "package"].map((icon) => (
                      <option key={icon} value={icon}>{icon.replace(/-/g, " ")}</option>
                    ))}
                  </select>
                  <Input
                    value={badge.title || ""}
                    onChange={(e) => {
                      const badges = [...(c.badges as Array<Record<string, string>>)];
                      badges[i] = { ...badges[i], title: e.target.value };
                      upd("badges", badges);
                    }}
                    placeholder="Title"
                    className="h-7 text-xs flex-1"
                  />
                </div>
                <Input
                  value={badge.description || ""}
                  onChange={(e) => {
                    const badges = [...(c.badges as Array<Record<string, string>>)];
                    badges[i] = { ...badges[i], description: e.target.value };
                    upd("badges", badges);
                  }}
                  placeholder="Description"
                  className="h-7 text-xs"
                />
                <button type="button" onClick={() => {
                  const badges = (c.badges as Array<Record<string, string>>).filter((_, j) => j !== i);
                  upd("badges", badges);
                }} className="text-xs text-destructive hover:underline">Remove</button>
              </div>
            ))}
            <button type="button" onClick={() => {
              const badges = [...(Array.isArray(c.badges) ? c.badges : []), { icon: "check-circle", title: "", description: "" }];
              upd("badges", badges);
            }} className="text-xs text-primary hover:underline flex items-center gap-1">
              <Plus className="h-3 w-3" /> Add Badge
            </button>
          </div>
        </div>
      );

    case "image_banner":
      return (
        <div className="space-y-3">
          <ConfigInput label="Image URL" value={(c.image_url as string) || ""} onChange={(v) => upd("image_url", v)} placeholder="https://..." />
          <ConfigInput label="Title" value={(c.title as string) || ""} onChange={(v) => upd("title", v)} />
          <ConfigInput label="Subtitle" value={(c.subtitle as string) || ""} onChange={(v) => upd("subtitle", v)} />
          <ConfigInput label="CTA Text" value={(c.cta_text as string) || ""} onChange={(v) => upd("cta_text", v)} />
          <ConfigInput label="CTA Link" value={(c.cta_link as string) || ""} onChange={(v) => upd("cta_link", v)} />
        </div>
      );

    case "custom_text":
      return (
        <div className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs">Content</Label>
            <Textarea
              value={(c.content as string) || ""}
              onChange={(e) => upd("content", e.target.value)}
              rows={4}
              className="text-xs"
            />
          </div>
          <ConfigSelect label="Alignment" value={(c.alignment as string) || "center"} onChange={(v) => upd("alignment", v)} options={[
            { value: "left", label: "Left" }, { value: "center", label: "Center" }, { value: "right", label: "Right" },
          ]} />
        </div>
      );

    case "spacer":
      return (
        <div className="space-y-3">
          <ConfigSelect label="Height" value={(c.height as string) || "md"} onChange={(v) => upd("height", v)} options={[
            { value: "sm", label: "Small" }, { value: "md", label: "Medium" }, { value: "lg", label: "Large" }, { value: "xl", label: "Extra Large" },
          ]} />
        </div>
      );

    default:
      return (
        <p className="text-xs text-muted-foreground">
          No configuration options for this block type.
        </p>
      );
  }
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
  const [expandedBlock, setExpandedBlock] = useState<number | null>(null);

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
    if (expandedBlock === index) setExpandedBlock(target);
    else if (expandedBlock === target) setExpandedBlock(index);
  }

  /**
   * Update a specific config key on a block.
   *
   * @param index - Block index.
   * @param key - Config key to update.
   * @param value - New value.
   */
  function updateBlockConfig(index: number, key: string, value: unknown) {
    setBlocks((prev) =>
      prev.map((b, i) =>
        i === index ? { ...b, config: { ...b.config, [key]: value } } : b
      )
    );
  }

  /**
   * Remove a block from the layout.
   * @param index - Block index to remove.
   */
  function removeBlock(index: number) {
    setBlocks((prev) => prev.filter((_, i) => i !== index));
    setExpandedBlock(null);
  }

  /** All available block types for the "Add Block" picker. */
  const AVAILABLE_BLOCK_TYPES = [
    "hero_banner", "featured_products", "categories_grid", "product_carousel",
    "reviews", "newsletter", "custom_text", "image_banner", "spacer",
    "testimonials", "countdown_timer", "video_banner", "trust_badges",
  ];

  /**
   * Add a new block with default config.
   * @param blockType - The type of block to add.
   */
  function addBlock(blockType: string) {
    const defaults: Record<string, Record<string, unknown>> = {
      hero_banner: { title: "Welcome", subtitle: "", cta_text: "Shop Now", cta_link: "/products", bg_type: "gradient", text_position: "center", height: "lg" },
      featured_products: { title: "Featured Products", count: 8, columns: 4, show_prices: true, show_badges: true },
      categories_grid: { title: "Shop by Category", columns: 3, show_product_count: true },
      product_carousel: { title: "Trending Now", count: 10, auto_scroll: false, interval: 4000, show_prices: true },
      reviews: { title: "Customer Reviews", count: 6, layout: "grid" },
      newsletter: { title: "Stay in the loop", subtitle: "Subscribe for updates", button_text: "Subscribe" },
      custom_text: { content: "Your custom text here", alignment: "center" },
      image_banner: { image_url: "", title: "", subtitle: "", cta_text: "", cta_link: "" },
      spacer: { height: "md" },
      testimonials: { title: "What People Are Saying", layout: "cards", items: [] },
      countdown_timer: { title: "Sale Ends In", target_date: "", subtitle: "", cta_text: "Shop the Sale", cta_link: "/products" },
      video_banner: { video_url: "", poster_url: "", title: "", subtitle: "", autoplay: false },
      trust_badges: { badges: [{ icon: "truck", title: "Free Shipping", description: "On orders over $50" }, { icon: "shield", title: "Secure Checkout", description: "SSL encrypted" }, { icon: "rotate-ccw", title: "Easy Returns", description: "30-day guarantee" }], columns: 3 },
    };
    const newBlock: BlockConfig = {
      type: blockType,
      enabled: true,
      config: defaults[blockType] || {},
    };
    setBlocks((prev) => [...prev, newBlock]);
    setExpandedBlock(blocks.length);
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

                {/* Typography weights */}
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="space-y-2">
                    <Label>Heading Weight</Label>
                    <div className="flex gap-1.5 flex-wrap">
                      {[
                        { v: "300", l: "Light" },
                        { v: "400", l: "Regular" },
                        { v: "500", l: "Medium" },
                        { v: "600", l: "Semi" },
                        { v: "700", l: "Bold" },
                        { v: "900", l: "Black" },
                      ].map((w) => (
                        <button
                          key={w.v}
                          type="button"
                          onClick={() => setTypography((p) => ({ ...p, heading_weight: w.v }))}
                          className={`px-2 py-1 text-xs rounded border transition-colors ${
                            (typography.heading_weight || "700") === w.v
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:border-muted-foreground/40"
                          }`}
                        >
                          {w.l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Body Weight</Label>
                    <div className="flex gap-1.5 flex-wrap">
                      {[
                        { v: "300", l: "Light" },
                        { v: "400", l: "Regular" },
                        { v: "500", l: "Medium" },
                      ].map((w) => (
                        <button
                          key={w.v}
                          type="button"
                          onClick={() => setTypography((p) => ({ ...p, body_weight: w.v }))}
                          className={`px-2 py-1 text-xs rounded border transition-colors ${
                            (typography.body_weight || "400") === w.v
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:border-muted-foreground/40"
                          }`}
                        >
                          {w.l}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Letter spacing & line height */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Letter Spacing</Label>
                    <div className="flex gap-1.5 flex-wrap">
                      {[
                        { v: "tight", l: "Tight" },
                        { v: "normal", l: "Normal" },
                        { v: "wide", l: "Wide" },
                      ].map((opt) => (
                        <button
                          key={opt.v}
                          type="button"
                          onClick={() => setTypography((p) => ({ ...p, letter_spacing: opt.v }))}
                          className={`px-2 py-1 text-xs rounded border transition-colors ${
                            (typography.letter_spacing || "normal") === opt.v
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:border-muted-foreground/40"
                          }`}
                        >
                          {opt.l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Line Height</Label>
                    <div className="flex gap-1.5 flex-wrap">
                      {[
                        { v: "compact", l: "Compact" },
                        { v: "normal", l: "Normal" },
                        { v: "relaxed", l: "Relaxed" },
                      ].map((opt) => (
                        <button
                          key={opt.v}
                          type="button"
                          onClick={() => setTypography((p) => ({ ...p, line_height: opt.v }))}
                          className={`px-2 py-1 text-xs rounded border transition-colors ${
                            (typography.line_height || "normal") === opt.v
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border hover:border-muted-foreground/40"
                          }`}
                        >
                          {opt.l}
                        </button>
                      ))}
                    </div>
                  </div>
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
                  Configure, reorder, and manage homepage sections
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {blocks.map((block, index) => (
                    <div
                      key={`${block.type}-${index}`}
                      className={`rounded-lg border transition-colors ${
                        block.enabled
                          ? "border-border bg-background"
                          : "border-border/50 bg-muted/30 opacity-60"
                      }`}
                    >
                      {/* Block header row */}
                      <div className="flex items-center gap-3 px-3 py-2">
                        <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium capitalize">
                            {block.type.replace(/_/g, " ")}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setExpandedBlock(expandedBlock === index ? null : index)}
                            className="p-1 rounded hover:bg-muted text-muted-foreground"
                            aria-label="Edit block config"
                          >
                            <Settings2 className="h-3.5 w-3.5" />
                          </button>
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
                              block.enabled ? "text-primary" : "text-muted-foreground"
                            }`}
                            aria-label={block.enabled ? "Disable block" : "Enable block"}
                          >
                            {block.enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                          </button>
                          <button
                            type="button"
                            onClick={() => removeBlock(index)}
                            className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                            aria-label="Remove block"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Expandable config panel */}
                      {expandedBlock === index && (
                        <div className="border-t border-border px-4 py-3 space-y-3 bg-muted/20">
                          <BlockConfigEditor
                            block={block}
                            index={index}
                            onUpdate={updateBlockConfig}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                  {blocks.length === 0 && (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                      No blocks configured. Add blocks below.
                    </p>
                  )}
                </div>

                {/* Add Block button */}
                <div className="mt-4">
                  <details className="group">
                    <summary className="flex items-center gap-2 cursor-pointer text-sm text-primary hover:text-primary/80 font-medium">
                      <Plus className="h-4 w-4" />
                      Add Block
                    </summary>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      {AVAILABLE_BLOCK_TYPES.map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => addBlock(type)}
                          className="text-left text-xs px-3 py-2 rounded-md border border-border hover:border-primary hover:bg-primary/5 transition-colors capitalize"
                        >
                          {type.replace(/_/g, " ")}
                        </button>
                      ))}
                    </div>
                  </details>
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
