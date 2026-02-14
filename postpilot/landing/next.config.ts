/**
 * Next.js 16 configuration for static landing page export.
 *
 * **For Developers:**
 *   - `output: "export"` generates a fully static site (no Node.js server needed).
 *   - `images.unoptimized: true` is required for static export since the Next.js
 *     image optimization API is not available without a server.
 *   - Deploy the `out/` directory to any static hosting (Vercel, Netlify, S3, etc.).
 *
 * **For QA Engineers:**
 *   - After `npm run build`, verify the `out/` directory contains index.html
 *     and a pricing/index.html for both routes.
 *   - Test by serving `out/` with any static file server (e.g. `npx serve out`).
 *
 * **For Project Managers:**
 *   - Static export means zero server costs for hosting landing pages.
 *   - Each service gets its own independently deployable landing page.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
