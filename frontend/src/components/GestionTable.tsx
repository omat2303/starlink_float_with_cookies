'use client';

import { useMemo, useState } from 'react';
import { api, type Client } from '@/lib/api';

const money = (n: number | null) =>
  n == null ? '—' : n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

type Row = {
  name: string;
  is_administered: boolean;
  is_paid_by_us: boolean;
  cost: string;
  price: string;
  currency: string;
  notes: string;
};

const toRow = (c: Client): Row => ({
  name: c.client_name,
  is_administered: c.gestion.is_administered,
  is_paid_by_us: c.gestion.is_paid_by_us,
  cost: c.gestion.cost?.toString() ?? '',
  price: c.gestion.price?.toString() ?? '',
  currency: c.gestion.currency ?? '',
  notes: c.gestion.notes ?? '',
});

export default function GestionTable({ clients }: { clients: Client[] }) {
  const [rows, setRows] = useState<Row[]>(() => clients.map(toRow));
  const [status, setStatus] = useState<Record<string, string>>({});

  const patch = (name: string, changes: Partial<Row>) =>
    setRows((prev) => prev.map((r) => (r.name === name ? { ...r, ...changes } : r)));

  const save = async (row: Row) => {
    setStatus((s) => ({ ...s, [row.name]: '…' }));
    try {
      await api.saveGestion({
        client_name: row.name,
        is_administered: row.is_administered,
        is_paid_by_us: row.is_paid_by_us,
        cost: row.cost === '' ? null : Number(row.cost),
        price: row.price === '' ? null : Number(row.price),
        currency: row.currency.trim() || null,
        notes: row.notes.trim() || null,
      });
      setStatus((s) => ({ ...s, [row.name]: '✓' }));
    } catch {
      setStatus((s) => ({ ...s, [row.name]: '!' }));
    }
  };

  const totals = useMemo(() => {
    const byCurrency: Record<string, { cost: number; price: number; n: number }> = {};
    for (const r of rows) {
      const cur = r.currency.trim().toUpperCase();
      if (!cur || (r.cost === '' && r.price === '')) continue;
      const t = (byCurrency[cur] ??= { cost: 0, price: 0, n: 0 });
      t.cost += Number(r.cost) || 0;
      t.price += Number(r.price) || 0;
      t.n += 1;
    }
    return byCurrency;
  }, [rows]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(totals).length === 0 ? (
          <div className="card text-gray-500 text-sm">
            Aún no hay costos cargados. Poné costo y precio por cliente abajo.
          </div>
        ) : (
          Object.entries(totals).map(([cur, t]) => {
            const margin = t.price - t.cost;
            return (
              <div key={cur} className="card">
                <p className="text-xs text-gray-500 uppercase tracking-wider">{cur} · {t.n} clientes</p>
                <p className="text-sm text-gray-400 mt-1">Costo: {money(t.cost)}</p>
                <p className="text-sm text-gray-400">Cobrado: {money(t.price)}</p>
                <p className={`text-xl font-bold mt-1 ${margin >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {margin >= 0 ? 'Ganancia' : 'Pérdida'}: {money(margin)}
                </p>
              </div>
            );
          })
        )}
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="text-gray-500 text-xs uppercase tracking-wider">
              <th className="text-left py-2 font-medium">Cliente</th>
              <th className="text-center py-2 font-medium">Administro</th>
              <th className="text-center py-2 font-medium">Pago yo</th>
              <th className="text-right py-2 font-medium">Costo/mes</th>
              <th className="text-right py-2 font-medium">Cobro/mes</th>
              <th className="text-center py-2 font-medium">Moneda</th>
              <th className="text-right py-2 font-medium">Margen</th>
              <th className="text-left py-2 font-medium">Notas</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const margin =
                r.cost !== '' && r.price !== '' ? Number(r.price) - Number(r.cost) : null;
              return (
                <tr key={r.name} className="border-t border-dark-600">
                  <td className="py-1.5 text-gray-200">{r.name}</td>
                  <td className="py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={r.is_administered}
                      onChange={(e) => {
                        patch(r.name, { is_administered: e.target.checked });
                        void save({ ...r, is_administered: e.target.checked });
                      }}
                    />
                  </td>
                  <td className="py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={r.is_paid_by_us}
                      onChange={(e) => {
                        patch(r.name, { is_paid_by_us: e.target.checked });
                        void save({ ...r, is_paid_by_us: e.target.checked });
                      }}
                    />
                  </td>
                  <td className="py-1.5 text-right">
                    <NumberCell
                      value={r.cost}
                      onChange={(v) => patch(r.name, { cost: v })}
                      onBlur={() => void save(r)}
                    />
                  </td>
                  <td className="py-1.5 text-right">
                    <NumberCell
                      value={r.price}
                      onChange={(v) => patch(r.name, { price: v })}
                      onBlur={() => void save(r)}
                    />
                  </td>
                  <td className="py-1.5 text-center">
                    <TextCell
                      value={r.currency}
                      placeholder="USD"
                      width="w-16"
                      onChange={(v) => patch(r.name, { currency: v })}
                      onBlur={() => void save(r)}
                    />
                  </td>
                  <td className={`py-1.5 text-right ${margin == null ? 'text-gray-500' : margin >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {money(margin)}
                  </td>
                  <td className="py-1.5">
                    <TextCell
                      value={r.notes}
                      placeholder="nota…"
                      width="w-40"
                      onChange={(v) => patch(r.name, { notes: v })}
                      onBlur={() => void save(r)}
                    />
                  </td>
                  <td className="py-1.5 pl-2 text-xs text-gray-500">{status[r.name] ?? ''}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NumberCell({
  value,
  onChange,
  onBlur,
}: {
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
}) {
  return (
    <input
      className="w-24 bg-dark-700 border border-dark-600 rounded px-1.5 py-0.5 text-xs text-right text-gray-200 focus:border-accent-blue outline-none"
      inputMode="decimal"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
    />
  );
}

function TextCell({
  value,
  onChange,
  onBlur,
  placeholder,
  width,
}: {
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  placeholder: string;
  width: string;
}) {
  return (
    <input
      className={`${width} bg-dark-700 border border-dark-600 rounded px-1.5 py-0.5 text-xs text-gray-200 focus:border-accent-blue outline-none`}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
    />
  );
}
