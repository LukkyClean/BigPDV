import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getFaturamento } from '../report.service';
import { reportKeys } from '../query.keys';

export function useFaturamentoQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => reportKeys.faturamento(unref(inicio), unref(fim))),
    queryFn: () => getFaturamento(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60, // 1 min — relatório não muda a cada segundo
  });
}
