/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Set output tracing root to avoid workspace root detection warnings
  // when multiple lockfiles exist in parent directories
  outputFileTracingRoot: process.cwd(),
  transpilePackages: ["@xyflow/react"],
};

export default nextConfig;
