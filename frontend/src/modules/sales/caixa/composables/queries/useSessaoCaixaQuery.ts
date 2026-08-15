import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { CONFIGURACOES_VENDAS_KEY } from '@/modules/configuracoes/composables/queries/useConfiguracoesVendasQuery';
import { getConfiguracoesVendas } from '@/modules/configuracoes/services/configuracoes.service';
import { REFETCH_REALTIME } from '@/core/config/queryIntervals';

import { getSessaoAtual } from '../../services/caixa.service';
import { caixaKeys } from '../../caixa.keys';

/**
 * O turno aberto do operador — e se o caixa existe para esta loja.
 *
 * DUAS DECISÕES QUE PROTEGEM QUEM NÃO USA CAIXA:
 *
 * 1. A query do turno só é DISPARADA com `controlar_caixa` ligado (`enabled`).
 *    Loja sem caixa nunca chama `/caixa/atual`.
 *
 * 2. A configuração é lida com a MESMA chave de `useConfiguracoesVendasQuery`
 *    (cache compartilhado, uma busca só) mas **sem herdar o `refetchInterval`
 *    dela**. Aquela query existe para a tela de Configurações, onde repetir a
 *    cada 5 min faz sentido; aqui ela ficaria montada o dia inteiro na tela de
 *    vendas, e o resultado seria polling permanente numa loja que sequer usa
 *    caixa. Cada observador do TanStack tem seu próprio intervalo, então
 *    declarar `refetchInterval: false` aqui não afeta a tela de Configurações.
 */
export function useSessaoCaixaQuery() {
  const configQuery = useQuery({
    queryKey: [CONFIGURACOES_VENDAS_KEY],
    queryFn: getConfiguracoesVendas,
    staleTime: Infinity,
    refetchInterval: false,
  });

  const config = configQuery.data;
  const caixaHabilitado = computed(() => config.value?.controlar_caixa === true);
  const exigeCaixaAberto = computed(() => config.value?.exigir_caixa_aberto === true);
  const fechamentoCego = computed(() => config.value?.fechamento_cego === true);

  const query = useQuery({
    queryKey: caixaKeys.atual(),
    queryFn: getSessaoAtual,
    enabled: caixaHabilitado,
    // O turno cruza terminais: dois caixas abertos ao mesmo tempo precisam ver
    // o estado um do outro sem F5. Mesmo intervalo das vendas.
    refetchInterval: REFETCH_REALTIME,
  });

  const sessao = computed(() => query.data.value ?? null);
  const caixaAberto = computed(() => sessao.value !== null);

  return {
    ...query,
    sessao,
    caixaAberto,
    caixaHabilitado,
    exigeCaixaAberto,
    fechamentoCego,
    carregandoConfig: configQuery.isLoading,
  };
}
