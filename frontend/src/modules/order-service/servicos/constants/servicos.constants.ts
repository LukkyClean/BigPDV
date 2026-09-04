import type { StatusFilter } from '../types/servicos.types';

export { SERVICOS_QUERY_KEY, SERVICOS_STATS_QUERY_KEY } from '../../shared/constants/queryKeys';
export const SERVICO_FISCAL_QUERY_KEY = 'servico-fiscal';
export const SERVICOS_STALE_TIME = 1000 * 60 * 5;
export const SEARCH_DEBOUNCE_MS = 300;

export const STATUS_FILTER_CONFIG: Record<
  StatusFilter,
  { label: string; class: string; color: string }
> = {
  ativos: {
    label: 'Ativos',
    class: 'bg-emerald-50 text-emerald-600',
    color: 'bg-emerald-500',
  },
  inativos: {
    label: 'Inativos',
    class: 'bg-red-50 text-red-600',
    color: 'bg-red-500',
  },
};
