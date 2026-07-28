import { computed, unref, type MaybeRef } from 'vue';
import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { dashboardService } from '../../services/dashboard.service';
import { dashboardKeys, DASHBOARD_STALE_TIME, REFETCH_DASHBOARD } from '../../constants/dashboard.constants';
import type { PeriodFilter } from '../../types/dashboard.types';

/** Tendência de faturamento da LOJA (Master). */
export function useTendenciaQuery(periodo: MaybeRef<PeriodFilter>) {
  return useQuery({
    queryKey: computed(() => dashboardKeys.tendencia(unref(periodo))),
    queryFn: () => dashboardService.getTendencia(unref(periodo)),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: REFETCH_DASHBOARD,
    placeholderData: keepPreviousData,
  });
}
