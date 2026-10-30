import { api, type Client, type Summary } from '@/lib/api';
import ClientList from '@/components/ClientList';
import SessionBar from '@/components/SessionBar';
import Link from 'next/link';

// Datos en vivo: sin esto Next intenta prerenderizar el panel en el build.
export const dynamic = 'force-dynamic';

const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

export default async function PanelPage() {
  let clients: Client[] = [];
  let summary: Summary | null = null;
  let error: string | null = null;

  try {
    [clients, summary] = await Promise.all([api.getClients(), api.getSummary()]);
  } catch {
    error = 'Sin conexión con el API. ¿Está corriendo el backend en localhost:8000?';
  }

  const antennas = clients.flatMap((c) => c.accounts.flatMap((a) => a.antennas));
  const on = antennas.filter((t) => t.active).length;
  const owe = clients.filter((c) => c.accounts.some((a) => (a.balance_due ?? 0) > 0)).length;
  const pct = (n: number, total: number) => (total === 0 ? 0 : Math.round((n / total) * 100));

  // Histograma real: cuántos clientes vencen cada uno de los próximos 7 días.
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    return d;
  });
  const buckets = days.map((d) => ({
    d,
    n: clients.filter((c) => c.next_due_date && dayKey(new Date(c.next_due_date)) === dayKey(d)).length,
  }));
  const maxBucket = Math.max(1, ...buckets.map((b) => b.n));

  return (
    <div className="min-h-screen grid-pattern">
      <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#0a0a0f]/80 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4 h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-indigo-900/40">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white leading-tight">StarPanel</h1>
                <p className="text-[11px] text-zinc-500 leading-tight">Lote Starlink por cliente</p>
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
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-sm">
            {error}
          </div>
        ) : (
          <>
            {summary && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                <Kpi
                  label="Clientes"
                  value={summary.clientes}
                  detail={`${owe} deben · ${summary.clientes - owe} al día`}
                  ratio={pct(summary.clientes - owe, summary.clientes)}
                  tone="emerald"
                />
                <Kpi
                  label="Antenas"
                  value={summary.antenas}
                  detail={`${on} encendidas · ${summary.antenas - on} apagadas`}
                  ratio={pct(on, summary.antenas)}
                  tone="indigo"
                />
                <Kpi
                  label="Suspendidas"
                  value={summary.suspendidas}
                  detail={`${pct(summary.suspendidas, summary.antenas)}% de las antenas`}
                  ratio={pct(summary.suspendidas, summary.antenas)}
                  tone="red"
                />
                <Kpi
                  label="Por vencer (7d)"
                  value={summary.por_vencer}
                  detail={`${summary.por_vencer_72h ?? 0} en menos de 72 h`}
                  ratio={pct(summary.por_vencer, summary.clientes)}
                  tone="amber"
                />
              </div>
            )}

            <div className="card mb-6">
              <div className="flex items-baseline justify-between mb-4">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  Vencimientos próximos 7 días
                </p>
                <p className="text-xs text-zinc-500">
                  {buckets.reduce((n, b) => n + b.n, 0)} clientes
                </p>
              </div>
              <div className="flex items-end gap-2 h-24">
                {buckets.map((b, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                    <span className="text-[11px] text-zinc-400">{b.n || ''}</span>
                    <div
                      className="w-full rounded-t-md bg-gradient-to-t from-indigo-600/70 to-indigo-400/80"
                      style={{ height: `${Math.max(2, (b.n / maxBucket) * 72)}px` }}
                      title={`${b.n} clientes el ${b.d.toLocaleDateString('es-ES')}`}
                    />
                    <span className="text-[10px] text-zinc-500">
                      {i === 0 ? 'hoy' : b.d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <ClientList clients={clients} />
          </>
        )}
      </main>
    </div>
  );
}

const tones = {
  emerald: 'from-emerald-500 to-emerald-400',
  indigo: 'from-indigo-500 to-indigo-400',
  red: 'from-red-500 to-red-400',
  amber: 'from-amber-500 to-amber-400',
} as const;

function Kpi({
  label,
  value,
  detail,
  ratio,
  tone,
}: {
  label: string;
  value: number;
  detail: string;
  ratio: number;
  tone: keyof typeof tones;
}) {
  return (
    <div className="card">
      <p className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</p>
      <p className="text-3xl font-semibold text-white mt-1">{value}</p>
      <div className="h-1.5 rounded-full bg-white/[0.06] mt-3 overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${tones[tone]}`}
          style={{ width: `${Math.min(100, ratio)}%` }}
        />
      </div>
      <p className="text-[11px] text-zinc-500 mt-1.5">{detail}</p>
    </div>
  );
}
