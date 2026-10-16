'use client';

import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';

// Botón de salir: cierra la sesión del panel (cookie httpOnly) y vuelve al login.
export default function PanelMenu() {
  const pathname = usePathname();
  if (pathname === '/login') return null;

  return (
    <button
      className="btn-secondary"
      style={{ position: 'fixed', left: 12, bottom: 12, zIndex: 9999 }}
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
  );
}
