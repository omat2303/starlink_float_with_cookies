/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Salida standalone: la que copia el Dockerfile, sin node_modules entero.
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
