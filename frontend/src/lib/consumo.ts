// El portal no entrega historial de consumo: sólo la foto del ciclo actual.
// Un límite de 100.000 GB es cómo Starlink reporta "ilimitado".
export const gb = (value: number | null) => (value == null ? '—' : `${value.toFixed(1)} GB`);

export const isUnlimited = (limit: number | null) => limit == null || limit >= 100000;

export const cyclePct = (consumed: number | null, limit: number | null) =>
  isUnlimited(limit) ? null : Math.min(100, ((consumed ?? 0) / (limit || 1)) * 100);
