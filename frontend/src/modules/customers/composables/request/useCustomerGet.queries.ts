import { ref, watch, computed } from 'vue';
import { refDebounced } from '@vueuse/core';
import { useQuery } from '@tanstack/vue-query';

import { getAllCustomers } from '../../services/customerGet.service';

import {
  CUSTOMER_QUERY_KEY,
  CUSTOMER_QUERY_STALE_TIME,
  REFETCH_CADASTROS,
} from '../../constants/customer.constant';

export function useCustomerQueryAll() {
  const searchQuery = ref('');
  const debouncedSearch = refDebounced(searchQuery, 500);
  /**
   * `true` traz só ativos; `false` traz TODOS (é o que a rota faz — não existe
   * modo "só inativos"). Quem decide é o filtro da tela: para achar um cliente
   * desativado é preciso pedir todos e estreitar depois.
   *
   * Ficou fixo em `true` por muito tempo, e nada na tela conseguia mexer nele —
   * era o que tornava o filtro "Desativado" impossível de dar resultado.
   */
  const onlyActive = ref<boolean>(true);
  /** Página maior quando se está garimpando inativos — ver `useCustomers`. */
  const pageLimit = ref<number | undefined>(undefined);
  const currentPage = ref<number>(1);

  watch([debouncedSearch, onlyActive, pageLimit], () => {
    currentPage.value = 1;
  });

  const query = useQuery({
    queryKey: [CUSTOMER_QUERY_KEY, debouncedSearch, onlyActive, pageLimit, currentPage],
    queryFn: () =>
      getAllCustomers({
        search: debouncedSearch.value || undefined,
        only_active: onlyActive.value,
        page: currentPage.value,
        limit: pageLimit.value,
      }),
    staleTime: CUSTOMER_QUERY_STALE_TIME,
    refetchInterval: REFETCH_CADASTROS,
  });

  const customers = computed(() => query.data.value?.items ?? []);
  const totalPages = computed(() => query.data.value?.total_pages ?? 1);
  const totalItems = computed(() => query.data.value?.total_items ?? 0);

  const setPage = (page: number) => {
    currentPage.value = page;
  };

  return {
    searchQuery,
    onlyActive,
    pageLimit,
    customers,
    totalPages,
    totalItems,
    currentPage,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    setPage,
  };
}
