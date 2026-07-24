import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getOSPerformance } from '../report.service';
import { reportKeys } from '../query.keys';

export function useOSPerformanceQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => reportKeys.osPerformance(unref(inicio), unref(fim))),
    queryFn: () => getOSPerformance(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60,
  });
}
