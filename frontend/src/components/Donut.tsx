import { cyclePct, gb, isUnlimited } from '@/lib/consumo';

const color = (pct: number | null) =>
  pct == null ? '#6366f1' : pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#6366f1';

// Anillo del ciclo: % usado dentro, color por umbral (<70 indigo, 70-90 ámbar,
// >90 rojo). Ilimitado muestra ∞: no hay contra qué comparar.
export default function Donut({
  consumed,
  limit,
  size = 46,
}: {
  consumed: number | null;
  limit: number | null;
  size?: number;
}) {
  const pct = cyclePct(consumed, limit);
  const r = 20;
  const circumference = 2 * Math.PI * r;

  return (
    <div
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      title={
        isUnlimited(limit)
          ? `${gb(consumed)} consumidos · plan ilimitado`
          : `${gb(consumed)} de ${gb(limit)} (${Math.round(pct ?? 0)}%)`
      }
    >
      <svg viewBox="0 0 48 48" className="h-full w-full -rotate-90">
        <circle cx="24" cy="24" r={r} fill="none" stroke="#27272a" strokeWidth="5" />
        <circle
          cx="24"
          cy="24"
          r={r}
          fill="none"
          stroke={color(pct)}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={pct == null ? circumference : `${(pct / 100) * circumference} ${circumference}`}
        />
      </svg>
      <span
        className="absolute font-semibold leading-none text-white"
        style={{ fontSize: size * 0.26 }}
      >
        {pct == null ? '∞' : Math.round(pct)}
      </span>
    </div>
  );
}
