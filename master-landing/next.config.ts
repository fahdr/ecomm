/**
 * Next.js configuration for the master suite landing page.
 *
 * Static export — deploy to any CDN or static hosting provider.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
