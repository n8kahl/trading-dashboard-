/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
    // Reduce serverless bundle size by excluding non-runtime files from tracing
    outputFileTracingExcludes: {
      '*': [
        '**/*.map',
        '**/__tests__/**',
        '**/tests/**',
        '**/docs/**',
        '**/.github/**',
        '**/.vscode/**',
        '**/coverage/**',
      ],
    },
  },
  // Avoid bundling image optimizer (not needed for this app)
  images: { unoptimized: true },
  // Skip ESLint during build in Vercel for faster deploys (CI should lint)
  eslint: { ignoreDuringBuilds: true },
};
module.exports = nextConfig;
