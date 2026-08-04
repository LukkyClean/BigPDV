import { SERVICOS_KEY } from '@/shared/constants/entityKeys';

// Ordens de Serviço
export const ORDENS_SERVICO_QUERY_KEY = 'ordens-servico';
export const ORDENS_SERVICO_STATS_QUERY_KEY = 'ordens-servico-stats';
export const FUNCIONARIOS_QUERY_KEY = 'funcionarios';
export const FORMAS_PAGAMENTO_QUERY_KEY = 'formas-pagamento';

// Serviços (catálogo)
// Prefixo canônico: a busca de serviço do item da OS pendura-se abaixo dele, então
// as mutations do catálogo só precisam invalidar SERVICOS_QUERY_KEY.
export const SERVICOS_QUERY_KEY = SERVICOS_KEY;
export const SERVICOS_STATS_QUERY_KEY = [SERVICOS_KEY, 'stats'] as const;
export const SERVICOS_OS_ITEM_QUERY_KEY = [SERVICOS_KEY, 'os-item'] as const;
