/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Set output tracing root to avoid workspace root detection warnings
  // when multiple lockfiles exist in parent directories
  outputFileTracingRoot: process.cwd(),
};

export default nextConfig;
