import axios from 'axios';

export interface Cycle {
  start: string | null;
  end: string | null;
  gb: number | null;
  limit_gb: number | null;
}

export interface AntennaOut {
  kit_number: string;
  service_line_number: string | null;
  nickname: string | null;
  custom_name: string | null;
  model: string;
  plan: string | null;
  active: boolean;
  is_suspended: boolean;
  is_standby?: boolean | null;
  subscription_status?: number | null;
  activation_date: string | null;
  transferable: boolean;
  cycles: Cycle[];
  data_cycle_gb: number | null;
  data_limit_gb: number | null;
  data_total_gb: number | null;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  last_connected: string | null;
}

export interface AccountOut {
  account_number: string;
  account_name: string;
  currency_code: string | null;
  region_code: string | null;
  balance_due: number | null;
  next_due_date: string | null;
  is_billing_suspended: boolean;
  antennas: AntennaOut[];
}

export interface Gestion {
  is_administered: boolean;
  is_paid_by_us: boolean;
  cost: number | null;
  price: number | null;
  currency: string | null;
  notes: string | null;
  margin: number | null;
}

export interface Client {
  client_name: string;
  is_suspended: boolean;
  currencies: string[];
  next_due_date: string | null;
  gestion: Gestion;
  accounts: AccountOut[];
}

export interface Summary {
  clientes: number;
  cuentas: number;
  antenas: number;
  suspendidas: number;
  por_vencer: number;
  por_vencer_72h?: number;
}

export interface SyncStatus {
  has_session: boolean;
  last_sync: string | null;
  accounts: number;
  antennas: number;
}

export interface SyncStats {
  accounts: number;
  antennas: number;
  errors: number;
}

// En el servidor (SSR) no existe el rewrite de Next: hay que ir directo al backend.
const baseURL =
  typeof window === 'undefined'
    ? process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    : '/api';

const client = axios.create({
  baseURL,
  timeout: 15000,
});

// nginx exige esta cabecera en los métodos que cambian estado (anti-CSRF).
client.defaults.headers.common['X-Requested-With'] = 'starpanel';

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const api = {
  panelLogin: async (password: string): Promise<void> => {
    await client.post('/panel/session', { password });
  },

  panelLogout: async (): Promise<void> => {
    await client.post('/panel/logout');
  },

  getClients: async (): Promise<Client[]> => {
    const { data } = await client.get<Client[]>('/clientes');
    return data;
  },

  getSummary: async (): Promise<Summary> => {
    const { data } = await client.get<Summary>('/resumen');
    return data;
  },

  getSyncStatus: async (): Promise<SyncStatus> => {
    const { data } = await client.get<SyncStatus>('/sync-status');
    return data;
  },

  login: async (cookie: string): Promise<{ authenticated: boolean }> => {
    const { data } = await client.post<{ authenticated: boolean }>('/auth/login', { cookie });
    return data;
  },

  // El sync real consulta ~57 cuentas: puede tardar minutos, sin timeout.
  triggerSync: async (): Promise<SyncStats> => {
    const { data } = await client.post<SyncStats>('/sync', null, { timeout: 0 });
    return data;
  },

  renameAntenna: async (kitNumber: string, customName: string): Promise<AntennaOut> => {
    const { data } = await client.patch<AntennaOut>(`/antennas/${encodeURIComponent(kitNumber)}`, {
      custom_name: customName,
    });
    return data;
  },

  saveGestion: async (payload: {
    client_name: string;
    is_administered?: boolean;
    is_paid_by_us?: boolean;
    cost?: number | null;
    price?: number | null;
    currency?: string | null;
    notes?: string | null;
  }): Promise<Gestion> => {
    const { data } = await client.put<Gestion>('/gestiones', payload);
    return data;
  },
};
