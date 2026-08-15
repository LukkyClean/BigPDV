import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getComissao } from '../report.service';
import { reportKeys } from '../query.keys';

export function useComissaoQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => reportKeys.comissao(unref(inicio), unref(fim))),
    queryFn: () => getComissao(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60,
  });
}
