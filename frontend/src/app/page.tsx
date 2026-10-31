import { api, type Client, type Summary } from '@/lib/api';
import ClientList from '@/components/ClientList';
import Donut from '@/components/Donut';
import { cyclePct, gb } from '@/lib/consumo';

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

  if (error) {
    return (
      <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-sm">
        {error}
      </div>
    );
  }

  const antennas = clients.flatMap((c) =>
    c.accounts.flatMap((a) => a.antennas.map((t) => ({ ...t, client: c.client_name })))
  );
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

  // Ilimitados quedan fuera del ranking: su % no existe.
  const topConsumo = antennas
    .map((t) => ({ ...t, pct: cyclePct(t.data_cycle_gb, t.data_limit_gb) }))
    .filter((t) => t.pct != null)
    .sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0))
    .slice(0, 5);

  return (
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
          <p className="text-xs text-zinc-500">{buckets.reduce((n, b) => n + b.n, 0)} clientes</p>
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

      <div className="card mb-6">
        <div className="flex items-baseline justify-between mb-4">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Consumo del ciclo</p>
          <p className="text-xs text-zinc-500">Top 5 por % usado</p>
        </div>
        {topConsumo.length === 0 ? (
          <p className="text-sm text-zinc-500">Sin planes con límite de datos.</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {topConsumo.map((t) => (
              <div
                key={t.kit_number}
                className="flex items-center gap-2 rounded-md border border-zinc-800/70 p-2"
              >
                <Donut consumed={t.data_cycle_gb} limit={t.data_limit_gb} size={40} />
                <div className="min-w-0">
                  <p className="truncate text-xs text-zinc-300">
                    {t.custom_name || t.nickname || t.kit_number}
                  </p>
                  <p className="truncate text-[11px] text-zinc-500">{t.client}</p>
                  <p className="text-[11px] text-zinc-400">
                    {gb(t.data_cycle_gb)} / {gb(t.data_limit_gb)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ClientList clients={clients} />
    </>
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
