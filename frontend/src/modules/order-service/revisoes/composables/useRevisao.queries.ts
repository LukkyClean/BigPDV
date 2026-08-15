import { computed, type Ref } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getRevisoesPendentes, getHistoricoKm } from '../services/revisao.service';
import { REVISOES_PENDENTES_QUERY_KEY } from '../../shared/constants/queryKeys';

/** Query dos veículos com revisão vencida (pós-venda de oficina). */
export function useRevisoesPendentes(enabled: Ref<boolean>) {
  return useQuery({
    queryKey: REVISOES_PENDENTES_QUERY_KEY,
    queryFn: getRevisoesPendentes,
    enabled,
    staleTime: 1000 * 60,
  });
}

/** Query do histórico de KM de um veículo (carrega quando há objetoId). */
export function useHistoricoKm(objetoId: Ref<number | null>) {
  return useQuery({
    queryKey: ['os-historico-km', objetoId] as const,
    queryFn: () => getHistoricoKm(objetoId.value as number),
    enabled: computed(() => objetoId.value != null),
    staleTime: 1000 * 60,
  });
}
