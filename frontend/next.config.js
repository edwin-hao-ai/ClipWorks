/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    // Use the internal Docker hostname for server-side rewrites so the Next.js
    // dev server can reach the backend container. Browser-side code still uses
    // NEXT_PUBLIC_API_URL (localhost:8000).
    const apiUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/static/:path*',
        destination: `${apiUrl}/api/static/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
