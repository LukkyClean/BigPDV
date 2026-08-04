import { CLIENTES_KEY } from '@/shared/constants/entityKeys';

export const BASE_CUSTOMER_URL = '/clientes';

// Prefixo compartilhado com a busca de cliente de Vendas e a lista da OS —
// invalidar aqui alcança as três. Ver shared/constants/entityKeys.ts.
export const CUSTOMER_QUERY_KEY = CLIENTES_KEY;
export const CUSTOMER_QUERY_STALE_TIME = 1000 * 60 * 5; // 5 min

export { REFETCH_CADASTROS } from '@/core/config/queryIntervals';
