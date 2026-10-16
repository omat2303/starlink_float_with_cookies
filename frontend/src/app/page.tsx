import { api, type Client, type Summary } from '@/lib/api';
import ClientList from '@/components/ClientList';
import SessionBar from '@/components/SessionBar';
import Link from 'next/link';

// Datos en vivo: sin esto Next intenta prerenderizar el panel en el build.
export const dynamic = 'force-dynamic';

export default async function PanelPage() {
  let clients: Client[] = [];
  let summary: Summary | null = null;
  let error: string | null = null;

  try {
    [clients, summary] = await Promise.all([api.getClients(), api.getSummary()]);
  } catch {
    error = 'Sin conexión con el API. ¿Está corriendo el backend en localhost:8000?';
  }

  return (
    <div className="min-h-screen bg-dark-900 grid-pattern">
      <header className="sticky top-0 z-50 bg-dark-800/95 backdrop-blur border-b border-dark-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4 h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-accent-blue/20 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-accent-blue"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">StarPanel</h1>
                <p className="text-xs text-gray-500">Lote Starlink por cliente</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Link href="/gestiones" className="btn-secondary">
                Gestiones y costos
              </Link>
              <SessionBar />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error ? (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm">
            {error}
          </div>
        ) : (
          <>
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
                <Stat label="Clientes" value={summary.clientes} />
                <Stat label="Cuentas" value={summary.cuentas} />
                <Stat label="Antenas" value={summary.antenas} />
                <Stat label="Suspendidas" value={summary.suspendidas} />
                <Stat label="Por vencer (7d)" value={summary.por_vencer} />
                <Stat label="Vence <72h" value={summary.por_vencer_72h ?? 0} />
              </div>
            )}

            <ClientList clients={clients} />
          </>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
