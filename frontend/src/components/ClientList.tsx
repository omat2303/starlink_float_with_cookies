'use client';

import { useMemo, useState } from 'react';
import { api, type AntennaOut, type Client } from '@/lib/api';

const gb = (value: number | null) => (value == null ? '—' : `${value.toFixed(1)} GB`);

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });

const money = (n: number) =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const daysSince = (iso: string) =>
  Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);

const hoursUntil = (iso: string) =>
  (new Date(iso).getTime() - Date.now()) / 3_600_000;

type Filter = 'todas' | 'suspendidas' | 'pausadas' | 'vencen';

// Suspendida = pago/suscripción suspendida. Pausada (standby) es otro estado.
const isSuspended = (c: Client) =>
  c.is_suspended || c.accounts.some((a) => a.antennas.some((t) => t.is_suspended));

const isPaused = (c: Client) =>
  c.accounts.some((a) => a.antennas.some((t) => t.is_standby));

const vencen72h = (c: Client) =>
  c.next_due_date != null && hoursUntil(c.next_due_date) <= 72 && hoursUntil(c.next_due_date) >= 0;

export default function ClientList({ clients }: { clients: Client[] }) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>('todas');
  const needle = query.trim().toLowerCase();

  const filtered = useMemo(() => {
    let list = clients;
    if (filter === 'suspendidas') list = list.filter(isSuspended);
    if (filter === 'pausadas') list = list.filter(isPaused);
    if (filter === 'vencen') list = list.filter(vencen72h);
    if (!needle) return list;
    return list.filter(
      (c) =>
        c.client_name.toLowerCase().includes(needle) ||
        c.accounts.some((a) =>
          a.antennas.some(
            (t) =>
              t.kit_number.toLowerCase().includes(needle) ||
              (t.custom_name ?? '').toLowerCase().includes(needle) ||
              (t.service_line_number ?? '').toLowerCase().includes(needle)
          )
        )
    );
  }, [clients, needle, filter]);

  const chips: { key: Filter; label: string }[] = [
    { key: 'todas', label: `Todas (${clients.length})` },
    { key: 'suspendidas', label: `Suspendidas (${clients.filter(isSuspended).length})` },
    { key: 'pausadas', label: `Pausadas (${clients.filter(isPaused).length})` },
    { key: 'vencen', label: `Vencen <72h (${clients.filter(vencen72h).length})` },
  ];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <input
          className="input max-w-md"
          placeholder="Buscar cliente, kit, nombre o SL…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {chips.map((c) => (
          <button
            key={c.key}
            onClick={() => setFilter(c.key)}
            className={`px-3 py-1.5 rounded-lg text-sm border ${
              filter === c.key
                ? 'bg-accent-blue/20 border-accent-blue text-accent-blue'
                : 'border-dark-600 text-gray-400 hover:text-gray-200'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-gray-500 text-sm">Sin resultados.</p>
      ) : (
        <div className="space-y-6">
          {filtered.map((c) => (
            <ClientBlock key={c.client_name} client={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function ClientBlock({ client }: { client: Client }) {
  const antennas = client.accounts.reduce((n, a) => n + a.antennas.length, 0);
  const regions = Array.from(
    new Set(client.accounts.map((a) => a.region_code).filter(Boolean) as string[])
  );
  const g = client.gestion;

  return (
    <section className="card">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3">
        <h2 className="text-lg font-bold text-white">{client.client_name}</h2>
        {client.is_suspended && <span className="badge-offline">Suspendido</span>}
        {isPaused(client) && <span className="badge-degraded">Pausado</span>}
        {!g.is_administered && <span className="badge-degraded">Solo acceso</span>}
        {g.is_paid_by_us && <span className="badge-degraded">Paga Omar</span>}
        {vencen72h(client) && <span className="badge-offline">Vence &lt;72h</span>}
        <span className="text-xs text-gray-500">{antennas} antena(s)</span>
        {regions.length > 0 && (
          <span className="text-xs text-gray-500">País: {regions.join(' / ')}</span>
        )}
        {client.currencies.length > 0 && (
          <span className="text-xs text-gray-500">Monedas: {client.currencies.join(' / ')}</span>
        )}
        {client.next_due_date && (
          <span className="text-xs text-gray-500">
            Próximo vencimiento: {fmtDate(client.next_due_date)}
          </span>
        )}
      </div>

      <div className="space-y-4">
        {client.accounts.map((a) => (
          <div key={a.account_number}>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400 mb-1">
              <span className="font-mono text-gray-300">{a.account_number}</span>
              {a.account_name !== client.client_name && <span>({a.account_name})</span>}
              {a.is_billing_suspended && <span className="text-red-400">Pago pendiente</span>}
              <span>
                Saldo: {a.balance_due == null ? '—' : `${money(a.balance_due)} ${a.currency_code ?? ''}`}
              </span>
              {a.next_due_date && <span>Vence: {fmtDate(a.next_due_date)}</span>}
            </div>

            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase tracking-wider">
                  <th className="text-left py-1 font-medium">Kit / Subscripción</th>
                  <th className="text-left py-1 font-medium">Modelo</th>
                  <th className="text-left py-1 font-medium">Plan</th>
                  <th className="text-right py-1 font-medium">Consumo (total)</th>
                  <th className="text-right py-1 font-medium">Ciclo</th>
                  <th className="text-left py-1 pl-4 font-medium">Suscripción</th>
                  <th className="text-left py-1 pl-4 font-medium">Antena</th>
                </tr>
              </thead>
              <tbody>
                {a.antennas.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-2 text-gray-600">
                      Sin antenas
                    </td>
                  </tr>
                ) : (
                  a.antennas.map((t) => <AntennaRow key={t.kit_number} antenna={t} />)
                )}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </section>
  );
}

function AntennaRow({ antenna }: { antenna: AntennaOut }) {
  const [cyclesOpen, setCyclesOpen] = useState(false);
  const hasCycles = antenna.cycles.length > 0;

  return (
    <>
      <tr className="border-t border-dark-600">
        <td className="py-1.5 font-mono text-gray-300">
          {antenna.kit_number}
          {antenna.service_line_number && (
            <div className="text-xs text-gray-500">{antenna.service_line_number}</div>
          )}
          {antenna.nickname && <div className="text-xs text-gray-500">✦ {antenna.nickname}</div>}
          <NameEditor antenna={antenna} />
        </td>
        <td className="py-1.5">{antenna.model}</td>
        <td className="py-1.5">
          {antenna.plan ?? '—'}
          {antenna.activation_date && (
            <div className="text-xs text-gray-500">
              Activa: {fmtDate(antenna.activation_date)} ({daysSince(antenna.activation_date)}d)
            </div>
          )}
          {antenna.transferable && (
            <div className="text-xs text-amber-400">&gt;90 días · transferible</div>
          )}
        </td>
        <td className="py-1.5 text-right">{gb(antenna.data_total_gb)}</td>
        <td className="py-1.5 text-right">
          {gb(antenna.data_cycle_gb)}
          {hasCycles && (
            <button
              onClick={() => setCyclesOpen((v) => !v)}
              className="block text-xs text-accent-blue hover:underline ml-auto"
            >
              ver ciclos ({antenna.cycles.length})
            </button>
          )}
        </td>
        <td className="py-1.5 pl-4">
          <span
            className={
              antenna.is_suspended
                ? 'badge-offline'
                : antenna.is_standby
                  ? 'badge-degraded'
                  : 'badge-online'
            }
          >
            {antenna.is_suspended ? 'Suspendida' : antenna.is_standby ? 'Pausada' : 'Activa'}
          </span>
        </td>
        <td className="py-1.5 pl-4">
          <span className={antenna.active ? 'badge-online' : 'badge-offline'}>
            {antenna.active ? 'Encendida' : 'Apagada'}
          </span>
        </td>
      </tr>
      {cyclesOpen && hasCycles && (
        <tr className="bg-dark-800/40">
          <td colSpan={7} className="py-2">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 uppercase tracking-wider">
                  <th className="text-left py-0.5 font-medium">Desde</th>
                  <th className="text-left py-0.5 font-medium">Hasta</th>
                  <th className="text-right py-0.5 font-medium">Consumo</th>
                  <th className="text-right py-0.5 font-medium">Límite</th>
                </tr>
              </thead>
              <tbody>
                {antenna.cycles.map((c, i) => (
                  <tr key={i} className="text-gray-300">
                    <td className="py-0.5">{c.start ? fmtDate(c.start) : '—'}</td>
                    <td className="py-0.5">{c.end ? fmtDate(c.end) : 'abierto'}</td>
                    <td className="py-0.5 text-right">{gb(c.gb)}</td>
                    <td className="py-0.5 text-right">{c.limit_gb == null ? '—' : gb(c.limit_gb)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  );
}

function NameEditor({ antenna }: { antenna: AntennaOut }) {
  const [value, setValue] = useState(antenna.custom_name ?? '');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const save = async () => {
    if ((antenna.custom_name ?? '') === value.trim()) return;
    setStatus('saving');
    try {
      await api.renameAntenna(antenna.kit_number, value.trim());
      setStatus('saved');
    } catch {
      setStatus('error');
    }
  };

  return (
    <div className="mt-0.5 flex items-center gap-1 max-w-[14rem]">
      <input
        className="w-32 bg-dark-700 border border-dark-600 rounded px-1.5 py-0.5 text-xs text-gray-200 focus:border-accent-blue outline-none"
        placeholder="nombre propio…"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setStatus('idle');
        }}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        }}
      />
      {status === 'saving' && <span className="text-xs text-gray-500">…</span>}
      {status === 'saved' && <span className="text-xs text-green-400">✓</span>}
      {status === 'error' && <span className="text-xs text-red-400">!</span>}
    </div>
  );
}
