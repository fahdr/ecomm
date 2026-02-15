/**
 * PostCSS configuration for Tailwind CSS v4.
 *
 * **For Developers:**
 *   - Tailwind v4 uses @tailwindcss/postcss instead of the legacy tailwindcss plugin.
 *   - No tailwind.config.js is needed; all theme customization happens in globals.css
 *     via the @theme directive and CSS variables.
 *   - This file should rarely need modification.
 */

const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
