import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getRanking } from '../report.service';
import { reportKeys } from '../query.keys';

export function useRankingQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => reportKeys.ranking(unref(inicio), unref(fim))),
    queryFn: () => getRanking(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60,
  });
}
