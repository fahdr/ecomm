/**
 * Next.js configuration for the service dashboard.
 *
 * **For Developers:**
 *   - output: "standalone" enables optimized Docker builds by producing
 *     a self-contained deployment bundle without node_modules.
 *   - Adjust rewrites/redirects here if the service API uses a non-standard path prefix.
 *
 * **For Project Managers:**
 *   - Standalone output reduces Docker image size significantly (from ~1GB to ~100MB).
 *   - This config is intentionally minimal; service-specific settings live in service.config.ts.
 */

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
