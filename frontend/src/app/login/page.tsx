'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.panelLogin(password);
      router.replace('/');
      router.refresh();
    } catch {
      setError('Contraseña incorrecta.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-dark-900 grid-pattern px-4">
      <form onSubmit={submit} className="card w-full max-w-sm">
        <h1 className="text-xl font-bold text-white">StarPanel</h1>
        <p className="text-xs text-gray-500 mt-1">Acceso restringido a OG Telecom</p>

        <input
          type="password"
          className="input w-full mt-6"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          required
        />

        <button type="submit" className="btn-primary w-full mt-4" disabled={busy || !password}>
          {busy ? 'Entrando…' : 'Entrar'}
        </button>

        {error && <p className="text-xs text-red-400 mt-3">{error}</p>}
      </form>
    </main>
  );
}
