'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, type SyncStatus } from '@/lib/api';

export default function SessionBar() {
  const router = useRouter();
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [cookie, setCookie] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.getSyncStatus());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const saveCookie = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await api.saveStarlinkCookie(cookie.trim());
      setCookie('');
      await refreshStatus();
      router.refresh();
    } catch {
      setMessage('No se pudo guardar la cookie.');
    } finally {
      setBusy(false);
    }
  };

  const syncNow = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const stats = await api.triggerSync();
      setMessage(`${stats.accounts} cuentas, ${stats.antennas} antenas.`);
      await refreshStatus();
      router.refresh();
    } catch (err) {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status;
      setMessage(
        httpStatus === 409
          ? 'Sesión vencida: vuelve a pegar la cookie.'
          : 'Falló la sincronización.'
      );
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  };

  if (status === null) return null; // API caído: la página ya avisa

  if (!status.has_session) {
    return (
      <div className="flex items-center gap-2">
        <textarea
          className="input w-72 h-10 py-1 text-xs resize-none"
          placeholder="Pega tu cookie de starlink.com"
          value={cookie}
          onChange={(e) => setCookie(e.target.value)}
        />
        <button className="btn-primary" disabled={busy || !cookie.trim()} onClick={saveCookie}>
          Guardar
        </button>
        {message && <span className="text-xs text-yellow-400">{message}</span>}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-400">
        {status.last_sync ? (
          <>Última sincronización: {new Date(status.last_sync).toLocaleString('es-ES')}</>
        ) : (
          <span className="text-red-400">sin sincronizar</span>
        )}
      </span>
      <button className="btn-primary" disabled={busy} onClick={syncNow}>
        {busy ? 'Sincronizando…' : 'Sincronizar ahora'}
      </button>
      {message && <span className="text-xs text-gray-300">{message}</span>}
    </div>
  );
}
