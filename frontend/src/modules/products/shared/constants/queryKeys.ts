import { REFETCH_CADASTROS } from '@/core/config/queryIntervals';
import { PRODUTOS_KEY } from '@/shared/constants/entityKeys';

// Prefixo compartilhado com a busca de produto de Vendas e do item da OS —
// invalidar aqui alcança as três. Ver shared/constants/entityKeys.ts.
export const PRODUTOS_QUERY_KEY = PRODUTOS_KEY;
export const PRODUTOS_STALE_TIME = 1000 * 60 * 5;
export const PRODUTOS_REFETCH_INTERVAL = REFETCH_CADASTROS;

export const FORNECEDORES_QUERY_KEY = 'fornecedores';
export const FORNECEDORES_STALE_TIME = 1000 * 60 * 5;
export const FORNECEDORES_REFETCH_INTERVAL = REFETCH_CADASTROS;