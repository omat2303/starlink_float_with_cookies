'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';
import SessionBar from './SessionBar';

// Marco tipo AdminCN: sidebar fija a la izquierda, topbar con el estado del sync.
// El login se queda sin marco (pantalla completa).
export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === '/login') return <>{children}</>;

  const inGestiones = pathname.startsWith('/gestiones');
  const title = inGestiones ? 'Gestiones y costos' : 'Panel';
  const subtitle = inGestiones
    ? 'Administración, quién paga y ganancia por cliente'
    : 'Lote Starlink por cliente';

  return (
    <div className="min-h-screen bg-[#09090b]">
      <aside className="fixed inset-y-0 left-0 z-40 w-60 border-r border-zinc-800 bg-[#0b0b0e] flex flex-col">
        <div className="h-14 px-4 flex items-center gap-2.5 border-b border-zinc-800">
          <div className="w-7 h-7 rounded-md bg-zinc-100 text-zinc-900 flex items-center justify-center text-sm font-bold">
            S
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-tight">StarPanel</p>
            <p className="text-[10px] text-zinc-500 leading-tight">OG Telecom</p>
          </div>
        </div>

        <nav className="flex-1 p-2 space-y-0.5">
          <NavItem href="/" label="Panel" active={!inGestiones} />
          <NavItem href="/gestiones" label="Gestiones y costos" active={inGestiones} />
        </nav>

        <div className="p-2 border-t border-zinc-800">
          <button
            className="w-full text-left px-3 py-2 rounded-md text-xs text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            onClick={async () => {
              try {
                await api.panelLogout();
              } finally {
                window.location.href = '/login';
              }
            }}
          >
            Salir
          </button>
        </div>
      </aside>

      <div className="pl-60">
        <header className="sticky top-0 z-30 h-14 border-b border-zinc-800 bg-[#09090b]/90 backdrop-blur px-6 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-sm font-semibold text-white leading-tight">{title}</h1>
            <p className="text-[11px] text-zinc-500 leading-tight">{subtitle}</p>
          </div>
          <SessionBar />
        </header>

        <main className="px-6 py-6">{children}</main>
      </div>
    </div>
  );
}

function NavItem({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={`block px-3 py-2 rounded-md text-xs font-medium transition-colors ${
        active
          ? 'bg-zinc-800 text-white'
          : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
      }`}
    >
      {label}
    </Link>
  );
}
