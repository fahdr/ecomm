/**
 * Next.js configuration for the Super Admin Dashboard.
 *
 * For Developers:
 *   Output is set to "standalone" for Docker deployments. The dashboard
 *   runs on port 3300 and communicates with the admin backend at port 8300.
 *
 * For Project Managers:
 *   This config controls how the admin dashboard is built and deployed.
 *   Standalone output bundles everything needed to run without node_modules.
 *
 * For QA Engineers:
 *   Run `npm run build` to verify the build succeeds. The standalone
 *   output is in `.next/standalone/`.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
