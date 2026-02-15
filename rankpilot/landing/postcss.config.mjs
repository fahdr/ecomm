/**
 * PostCSS configuration for Tailwind CSS v4.
 *
 * Uses the `@tailwindcss/postcss` plugin which is the recommended
 * approach for Tailwind v4 integration with Next.js.
 *
 * **For Developers:**
 *   No additional PostCSS plugins are needed. Tailwind v4 handles
 *   all CSS processing including nesting, custom properties, and
 *   the new `@theme` directive.
 */
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
