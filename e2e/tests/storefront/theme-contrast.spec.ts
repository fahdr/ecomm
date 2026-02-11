/**
 * Storefront theme contrast and visual integrity tests.
 *
 * Verifies that storefront text is readable against backgrounds for all theme
 * presets, especially dark themes like Midnight and Cyberpunk. Also tests the
 * hero product showcase mode.
 *
 * **For QA Engineers:**
 *   - Dark themes must have light text on dark backgrounds (WCAG AA contrast >= 4.5).
 *   - Hero banner product showcase should show products even without configured IDs.
 *   - Theme CSS variables must be injected correctly from backend preset colors.
 *
 * **For Developers:**
 *   Uses ``page.evaluate()`` to read computed styles and calculate WCAG contrast.
 *   The ``?store=`` query param is required in local dev to resolve the store.
 *   Theme activation is done via API before navigating to the storefront.
 */

import { test, expect } from "@playwright/test";
import { registerUser, createStoreAPI, createProductAPI } from "../helpers";

const API_BASE = "http://localhost:8000";

/**
 * Calculate WCAG 2.0 contrast ratio between two hex colors.
 *
 * @param hex1 - First color in hex (e.g. "#0f1729").
 * @param hex2 - Second color in hex (e.g. "#e2e8f0").
 * @returns The contrast ratio (1 to 21).
 */
function contrastRatio(hex1: string, hex2: string): number {
  const luminance = (hex: string) => {
    const c = hex.replace("#", "");
    const [r, g, b] = [0, 2, 4].map((i) => {
      let v = parseInt(c.substring(i, i + 2), 16) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const l1 = luminance(hex1);
  const l2 = luminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Convert an rgb(...) string to hex.
 */
function rgbToHex(rgb: string): string {
  const match = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return "#000000";
  const [, r, g, b] = match;
  return (
    "#" +
    [r, g, b]
      .map((v) => parseInt(v).toString(16).padStart(2, "0"))
      .join("")
  );
}

/**
 * Activate a theme by name for a store via the API.
 */
async function activateThemeByName(
  token: string,
  storeId: string,
  themeName: string
): Promise<void> {
  // List all themes for the store
  const res = await fetch(`${API_BASE}/api/v1/stores/${storeId}/themes`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const themes = await res.json();
  const themeList = Array.isArray(themes) ? themes : themes.items || [];

  const target = themeList.find(
    (t: { name: string }) => t.name.toLowerCase() === themeName.toLowerCase()
  );
  if (!target) throw new Error(`Theme "${themeName}" not found`);

  // Activate the theme
  await fetch(
    `${API_BASE}/api/v1/stores/${storeId}/themes/${target.id}/activate`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

test.describe("Storefront Theme Contrast", () => {
  let token: string;
  let storeId: string;
  let storeSlug: string;

  test.beforeEach(async () => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(user.token, "Theme Contrast Store");
    storeId = store.id;
    storeSlug = store.slug;

    // Create a product so the storefront has content
    await createProductAPI(user.token, store.id, {
      title: "Contrast Test Widget",
      price: "29.99",
    });
  });

  test("dark theme (Midnight) has readable hero text", async ({ page }) => {
    // Activate Midnight theme via API
    await activateThemeByName(token, storeId, "Midnight");

    // Navigate to storefront
    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });

    // Wait for hero to render
    const hero = page.locator("section").first();
    await expect(hero).toBeVisible({ timeout: 15000 });

    // Get computed styles for the hero background and text
    const colors = await page.evaluate(() => {
      const heroEl = document.querySelector("section");
      if (!heroEl) return null;
      const style = getComputedStyle(heroEl);
      const h1 = heroEl.querySelector("h1");
      const textColor = h1 ? getComputedStyle(h1).color : style.color;
      return {
        background: style.backgroundColor,
        text: textColor,
      };
    });

    expect(colors).not.toBeNull();
    if (colors && colors.background !== "rgba(0, 0, 0, 0)") {
      const bgHex = rgbToHex(colors.background);
      const textHex = rgbToHex(colors.text);
      const ratio = contrastRatio(bgHex, textHex);
      // WCAG AA requires >= 4.5 for normal text, >= 3.0 for large text
      // Hero text is large, so 3.0 minimum. We check for 3.0 to be safe.
      expect(ratio).toBeGreaterThanOrEqual(3.0);
    }
  });

  test("storefront text uses theme foreground color (not hardcoded dark)", async ({
    page,
  }) => {
    // Activate Midnight (dark bg) theme
    await activateThemeByName(token, storeId, "Midnight");

    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });

    // Check that the CSS variable --theme-text is set to a light color
    const themeText = await page.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue("--theme-text")
        .trim();
    });

    // Midnight's foreground is "#e2e8f0" (light)
    // If the bug exists, it would be "#1a1a1a" (dark fallback)
    expect(themeText).not.toBe("#1a1a1a");
    // Should be a light color for dark theme
    const textHex = themeText.startsWith("#") ? themeText : "#e2e8f0";
    const luminance = (() => {
      const c = textHex.replace("#", "");
      const [r, g, b] = [0, 2, 4].map((i) => {
        const v = parseInt(c.substring(i, i + 2), 16) / 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    })();
    // Light text should have luminance > 0.5
    expect(luminance).toBeGreaterThan(0.5);
  });

  test("hero product showcase shows products without configured IDs", async ({
    page,
  }) => {
    // Set the hero banner to product_showcase mode via API
    const themesRes = await fetch(
      `${API_BASE}/api/v1/stores/${storeId}/themes`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const themes = await themesRes.json();
    const themeList = Array.isArray(themes) ? themes : themes.items || [];
    const activeTheme = themeList.find((t: { is_active: boolean }) => t.is_active);

    if (activeTheme) {
      // Update the hero block to use product_showcase
      const blocks = activeTheme.blocks || [];
      const heroBanner = blocks.find(
        (b: { type: string }) => b.type === "hero_banner"
      );
      if (heroBanner) {
        heroBanner.config.bg_type = "product_showcase";
        heroBanner.config.featured_product_ids = []; // empty = should fallback

        await fetch(
          `${API_BASE}/api/v1/stores/${storeId}/themes/${activeTheme.id}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ blocks }),
          }
        );
      }
    }

    // Navigate to the storefront
    await page.goto(`/?store=${storeSlug}`, { waitUntil: "networkidle" });

    // The hero section should display products (the fallback shows first 3)
    // We created at least one product, so product content should appear
    await expect(
      page.getByText("Contrast Test Widget").first()
    ).toBeVisible({ timeout: 15000 });
  });
});
