import { computed, ref, watch } from 'vue';
import { refDebounced } from '@vueuse/core';
import { useQuery } from '@tanstack/vue-query';

import { getServicos, getServicosStats } from '../services/servicos.service';
import { SERVICOS_QUERY_KEY, SERVICOS_STATS_QUERY_KEY, SERVICOS_STALE_TIME } from '../constants/servicos.constants';
import { REFETCH_CADASTROS } from '@/core/config/queryIntervals';
import type { QueryParams, StatusFilter } from '../types/servicos.types';

export function useServicosQuery(params?: QueryParams) {
  const searchQuery = ref<string | undefined>(undefined);
  const debouncedSearchQuery = refDebounced(searchQuery, 1000);
  const activeFilterQuery = ref<StatusFilter | null>(null);
  const currentPage = ref(1);

  const filterQuery = computed<boolean | undefined>(() => {
    if (activeFilterQuery.value === 'ativos') return true;
    if (activeFilterQuery.value === 'inativos') return false;
    return undefined;
  });

  watch([debouncedSearchQuery, filterQuery], () => {
    currentPage.value = 1;
  });

  const query = useQuery({
    queryKey: [SERVICOS_QUERY_KEY, debouncedSearchQuery, filterQuery, currentPage],
    queryFn: () => getServicos({
      search: debouncedSearchQuery.value,
      active: filterQuery.value,
      page: currentPage.value,
      ...params,
    }),
    staleTime: SERVICOS_STALE_TIME,
    refetchInterval: REFETCH_CADASTROS,
  });

  const services = computed(() => query.data.value?.items ?? []);
  const totalPages = computed(() => query.data.value?.total_pages ?? 1);
  const totalItems = computed(() => query.data.value?.total_items ?? 0);

  function setPage(page: number) {
    currentPage.value = page;
  }

  return {
    searchQuery,
    activeFilterQuery,
    currentPage,
    services,
    totalPages,
    totalItems,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    setPage,
    refetch: query.refetch,
  };
}

export function useServicosStatsQuery() {
  const query = useQuery({
    queryKey: SERVICOS_STATS_QUERY_KEY,
    queryFn: getServicosStats,
    staleTime: SERVICOS_STALE_TIME,
    refetchInterval: REFETCH_CADASTROS,
  });

  const stats = computed(() => ({
    total: query.data.value?.total ?? 0,
    ativos: query.data.value?.ativos ?? 0,
    inativos: query.data.value?.inativos ?? 0,
    mediaValor: query.data.value?.media_valor ?? 0,
  }));

  return {
    stats,
    isLoading: query.isLoading,
  };
}
