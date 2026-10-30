import { api, type Client, type Summary } from '@/lib/api';
import ClientList from '@/components/ClientList';

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

  if (error) {
    return (
      <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-sm">
        {error}
      </div>
    );
  }

  return (
    <>
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 mb-6">
          <Stat label="Clientes" value={summary.clientes} />
          <Stat label="Cuentas" value={summary.cuentas} />
          <Stat label="Antenas" value={summary.antenas} />
          <Stat label="Suspendidas" value={summary.suspendidas} tone="red" />
          <Stat label="Por vencer (7d)" value={summary.por_vencer} tone="amber" />
          <Stat label="Vence <72h" value={summary.por_vencer_72h ?? 0} tone="red" />
        </div>
      )}

      <ClientList clients={clients} />
    </>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: 'red' | 'amber';
}) {
  return (
    <div className="card">
      <p className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</p>
      <p
        className={`text-2xl font-semibold mt-1 ${
          tone === 'red' ? 'text-red-400' : tone === 'amber' ? 'text-amber-400' : 'text-white'
        }`}
      >
        {value}
      </p>
    </div>
  );
}
