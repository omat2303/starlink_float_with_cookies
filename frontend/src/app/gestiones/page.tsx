import { api, type Client } from '@/lib/api';
import GestionTable from '@/components/GestionTable';

export const dynamic = 'force-dynamic';

export default async function GestionesPage() {
  let clients: Client[] = [];
  let error: string | null = null;

  try {
    clients = await api.getClients();
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

  return <GestionTable clients={clients} />;
}
