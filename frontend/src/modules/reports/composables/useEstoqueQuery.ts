import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getEstoque } from '../report.service';
import { reportKeys } from '../query.keys';

export function useEstoqueQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => reportKeys.estoque(unref(inicio), unref(fim))),
    queryFn: () => getEstoque(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60,
  });
}
