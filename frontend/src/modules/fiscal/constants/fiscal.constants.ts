import { REFETCH_DASHBOARD } from '@/core/config/queryIntervals';

export const FISCAL_STALE_TIME = 1000 * 30;
export const FISCAL_REFETCH_INTERVAL = REFETCH_DASHBOARD;

export const fiscalKeys = {
  documentos: (filters?: any, page?: number) =>
    ['fiscal', 'documentos', filters, page] as const,
  resumo: () => ['fiscal', 'resumo'] as const,
  pendencias: () => ['fiscal', 'pendencias'] as const,
  documento: (id: number) => ['fiscal', 'documento', id] as const,
};

export const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  PENDENTE: { bg: 'bg-amber-100', text: 'text-amber-700' },
  PROCESSANDO: { bg: 'bg-blue-100', text: 'text-blue-700' },
  AUTORIZADA: { bg: 'bg-green-100', text: 'text-green-700' },
  REJEITADA: { bg: 'bg-red-100', text: 'text-red-600' },
  CANCELADA: { bg: 'bg-zinc-100', text: 'text-zinc-500' },
  DENEGADA: { bg: 'bg-red-100', text: 'text-red-600' },
};

export const STATUS_FILTER_OPTIONS = [
  { value: 'PENDENTE', label: 'Pendentes' },
  { value: 'PROCESSANDO', label: 'Processando' },
  { value: 'AUTORIZADA', label: 'Autorizadas' },
  { value: 'REJEITADA', label: 'Rejeitadas' },
  { value: 'CANCELADA', label: 'Canceladas' },
  { value: 'DENEGADA', label: 'Denegadas' },
];

export const TIPO_FILTER_OPTIONS = [
  { value: 'NFE', label: 'NF-e' },
  { value: 'NFCE', label: 'NFC-e' },
  { value: 'NFSE', label: 'NFS-e' },
];

export const TIPO_LABELS: Record<string, string> = {
  NFE: 'NF-e',
  NFCE: 'NFC-e',
  NFSE: 'NFS-e',
};

export const ORIGEM_LABELS: Record<string, string> = {
  VENDA: 'Venda',
  ORDEM_SERVICO: 'OS',
};
