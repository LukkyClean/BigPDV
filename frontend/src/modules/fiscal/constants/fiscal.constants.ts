import { REFETCH_DASHBOARD } from '@/core/config/queryIntervals';
import type { DocumentoFiscalFilters } from '../types/fiscal.types';

export const FISCAL_STALE_TIME = 1000 * 30;
export const FISCAL_REFETCH_INTERVAL = REFETCH_DASHBOARD;

export const fiscalKeys = {
  /**
   * Prefixo de TUDO do fiscal. Invalidar `all` alcança documentos, resumo,
   * pendências e o resto, porque todas as chaves abaixo penduram dele.
   *
   * Existe porque o código chamava `fiscalKeys.all` sem que a chave existisse:
   * em runtime isso vira `queryKey: undefined`, e o TanStack entende
   * "invalide TUDO" -- o app inteiro refetchava a cada correção de venda.
   */
  all: ['fiscal'] as const,
  documentos: (filters?: DocumentoFiscalFilters, page?: number) =>
    ['fiscal', 'documentos', filters, page] as const,
  resumo: () => ['fiscal', 'resumo'] as const,
  pendencias: () => ['fiscal', 'pendencias'] as const,
  documento: (id: number) => ['fiscal', 'documento', id] as const,
  configuracao: () => ['fiscal', 'configuracao'] as const,
  historico: (id: number) => ['fiscal', 'historico', id] as const,
  verificacaoBatch: (ids: number[]) => ['fiscal', 'verificacao-batch', ...ids] as const,
};

/**
 * Cores por status do documento fiscal.
 *
 * `border` faltava aqui e o drawer de detalhes já a consumia (a bolinha da
 * linha do tempo desenha `border-2` e pintava com a cor errada). Está no tipo
 * agora para que faltar de novo vire erro de compilação, e não borda cinza.
 */
export const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  PENDENTE: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  PROCESSANDO: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  AUTORIZADA: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' },
  REJEITADA: { bg: 'bg-red-100', text: 'text-red-600', border: 'border-red-300' },
  CANCELADA: { bg: 'bg-zinc-100', text: 'text-zinc-500', border: 'border-zinc-300' },
  DENEGADA: { bg: 'bg-red-100', text: 'text-red-600', border: 'border-red-300' },
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
