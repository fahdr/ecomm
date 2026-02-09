/**
 * Block Renderer -- maps block type strings to their React components and
 * renders enabled blocks in the order they appear in the theme configuration.
 *
 * This is the single entry point for the storefront homepage's composable
 * block system.  The parent layout fetches the store theme (which includes an
 * ordered ``blocks`` array), then passes it here for rendering.
 *
 * **For Developers:**
 *   Import this component in the storefront homepage and pass the theme's
 *   ``blocks`` array.  To add a new block type, create the component file in
 *   this directory and register it in the ``BLOCK_MAP`` below.  Each block
 *   component receives ``config: Record<string, unknown>`` as its only prop.
 *
 * **For QA Engineers:**
 *   - Disabled blocks (``enabled: false``) must not render.
 *   - Blocks render in the exact order specified by the ``blocks`` array.
 *   - Unknown block types are silently skipped (no crash, no visible output).
 *   - An empty ``blocks`` array renders nothing.
 *
 * **For Project Managers:**
 *   The block renderer is the backbone of the store builder feature.  Store
 *   owners configure which blocks appear on their homepage and in what order.
 *   This component translates that configuration into the live storefront.
 *
 * **For End Users:**
 *   The sections you see on a store's homepage (hero banners, product grids,
 *   newsletter forms, etc.) are all driven by this renderer based on the
 *   store owner's chosen theme and layout.
 *
 * @module blocks/block-renderer
 */

import type { ThemeBlock } from "@/lib/types";

import { HeroBanner } from "./hero-banner";
import { FeaturedProducts } from "./featured-products";
import { CategoriesGrid } from "./categories-grid";
import { Newsletter } from "./newsletter";
import { CustomText } from "./custom-text";
import { ImageBanner } from "./image-banner";
import { Spacer } from "./spacer";
import { ReviewsBlock } from "./reviews-block";

/**
 * Registry that maps a block ``type`` string (as stored in the theme config)
 * to the React component responsible for rendering that block.
 *
 * @remarks
 * Keys must match the ``type`` values used by the backend theme system
 * (see ``backend/app/constants/themes.py``).
 */
const BLOCK_MAP: Record<
  string,
  React.ComponentType<{ config: Record<string, unknown> }>
> = {
  hero_banner: HeroBanner,
  featured_products: FeaturedProducts,
  categories_grid: CategoriesGrid,
  newsletter: Newsletter,
  custom_text: CustomText,
  image_banner: ImageBanner,
  spacer: Spacer,
  reviews: ReviewsBlock,
};

/**
 * Props for the {@link BlockRenderer} component.
 */
interface BlockRendererProps {
  /** Ordered array of theme blocks from the store's theme configuration. */
  blocks: ThemeBlock[];
}

/**
 * Render an ordered list of theme blocks.
 *
 * Iterates over the ``blocks`` array, skips disabled entries and unknown
 * types, and renders each recognized block in order.
 *
 * @param props - Component props containing the blocks array.
 * @param props.blocks - The ordered theme blocks to render.
 * @returns A fragment containing all enabled block components.
 *
 * @example
 * ```tsx
 * import { BlockRenderer } from "@/components/blocks/block-renderer";
 * import type { ThemeBlock } from "@/lib/types";
 *
 * const blocks: ThemeBlock[] = theme.blocks;
 * <BlockRenderer blocks={blocks} />
 * ```
 */
export function BlockRenderer({ blocks }: BlockRendererProps) {
  return (
    <>
      {blocks.map((block, index) => {
        // Skip disabled blocks
        if (!block.enabled) return null;

        // Look up the component for this block type
        const Component = BLOCK_MAP[block.type];
        if (!Component) return null;

        return (
          <Component
            key={`${block.type}-${index}`}
            config={block.config}
          />
        );
      })}
    </>
  );
}
