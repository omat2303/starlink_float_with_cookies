/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Salida standalone: la que copia el Dockerfile, sin node_modules entero.
  output: 'standalone',
  // El proxy de `next dev` corta a los 30 s por defecto y un sync completo tarda
  // más (50+ cuentas): el panel recibía un 500 mientras el backend seguía
  // sincronizando. En Docker no aplica: nginx va directo al backend (900s).
  experimental: { proxyTimeout: 900000 },
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
