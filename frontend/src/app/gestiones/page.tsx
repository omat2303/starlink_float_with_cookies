import Link from 'next/link';
import { api, type Client } from '@/lib/api';
import GestionTable from '@/components/GestionTable';

export const dynamic = 'force-dynamic';

export default async function GestionesPage() {
  let clients: Client[] = [];
  let error: string | null = null;

  try {
    clients = await api.getClients();
  } catch {
    error = 'Sin conexión con el API. ¿Está corriendo el backend en localhost:8000?';
  }

  return (
    <div className="min-h-screen bg-dark-900 grid-pattern">
      <header className="sticky top-0 z-50 bg-dark-800/95 backdrop-blur border-b border-dark-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4 h-16">
            <div>
              <h1 className="text-xl font-bold text-white">Gestiones y costos</h1>
              <p className="text-xs text-gray-500">Administración, quién paga y ganancia por cliente</p>
            </div>
            <Link href="/" className="btn-secondary">
              ← Volver al panel
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error ? (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm">
            {error}
          </div>
        ) : (
          <GestionTable clients={clients} />
        )}
      </main>
    </div>
  );
}
