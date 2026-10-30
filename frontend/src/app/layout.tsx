import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Shell from '@/components/Shell';
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
      <body className={`${inter.className} bg-[#09090b] text-zinc-200 antialiased`}>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
