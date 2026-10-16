import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import PanelMenu from '@/components/PanelMenu';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'StarLink Fleet Manager',
  description: 'Dashboard de gestión de flota Starlink',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="dark">
      <body className={`${inter.className} bg-dark-900 text-gray-100 antialiased`}>
        <PanelMenu />
        {children}
      </body>
    </html>
  );
}
