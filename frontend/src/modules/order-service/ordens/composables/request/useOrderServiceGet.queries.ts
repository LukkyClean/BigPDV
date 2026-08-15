import { ref, watch, computed } from 'vue';
import type { Ref } from 'vue';
import { refDebounced } from '@vueuse/core';
import { useQuery } from '@tanstack/vue-query';

import { getAllOs, getUniqueOS, getStatsOS, getOsByClienteId } from '../../services/orderServiceGet.service';

import { OsStatusEnumDataType } from '../../schemas/enums/osEnums.schema';
import { isDesfechoKey, type OsEstadoKey } from '../../constants/ordemServico.constants';

import {
  ORDER_SERVICE_QUERY_KEY,
  ORDER_SERVICE_QUERY_STALE_TIME,
  ORDER_SERVICE_REFETCH_INTERVAL,
} from '../../constants/core.constant';

export function useOrderServiceQueryAll() {
  const searchQuery = ref<string | undefined>(undefined);
  const deboucedSearchQuery = refDebounced(searchQuery, 1000);
  // Uma seleção só na UI, dois parâmetros possíveis na API: o menu de filtro
  // lista status do fluxo E desfechos ("Condenado"/"Sem Reparo"), que no backend
  // são o campo `situacao_equipamento`.
  const activeStatusFilterQuery = ref<OsEstadoKey | undefined>(undefined);
  const activePriorityFilterQuery = ref<boolean>(false);
  const currentPage = ref<number>(1);

  watch([deboucedSearchQuery, activeStatusFilterQuery, activePriorityFilterQuery], () => {
    currentPage.value = 1;
  });

  const filtroEstado = computed(() => {
    const key = activeStatusFilterQuery.value;
    if (!key) return {};
    if (isDesfechoKey(key)) return { situacao_equipamento: key };
    return { status: key as OsStatusEnumDataType };
  });

  const query = useQuery({
    queryKey: [
      ORDER_SERVICE_QUERY_KEY,
      deboucedSearchQuery,
      activeStatusFilterQuery,
      activePriorityFilterQuery,
      currentPage,
    ],
    queryFn: () =>
      getAllOs({
        search: deboucedSearchQuery.value,
        ...filtroEstado.value,
        priority_sort: activePriorityFilterQuery.value,
        page: currentPage.value,
      }),
    staleTime: ORDER_SERVICE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });

  const orderServices = computed(() => query.data.value?.items ?? []);
  const totalPages = computed(() => query.data.value?.total_pages ?? 1);
  const totalItems = computed(() => query.data.value?.total_items ?? 0);

  const setPage = (page: number) => {
    currentPage.value = page;
  };

  return {
    searchQuery,
    activeStatusFilterQuery,
    activePriorityFilterQuery,
    orderServices,
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

export function useOrderServiceQueryUnique(numero_os: string) {
  const query = useQuery({
    queryKey: [ORDER_SERVICE_QUERY_KEY, numero_os],
    queryFn: () => getUniqueOS(numero_os),
    staleTime: ORDER_SERVICE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });

  const uniqueOs = query.data.value;

  return {
    uniqueOs,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}

export function useOrderServiceQueryStats() {
  const query = useQuery({
    queryKey: [ORDER_SERVICE_QUERY_KEY],
    queryFn: () => getStatsOS(),
    staleTime: ORDER_SERVICE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });

  const stats = computed(() => ({
    total: query.data.value?.total ?? 0,
    abertas: query.data.value?.abertas ?? 0,
    finalizadas: query.data.value?.finalizadas ?? 0,
    ticket_medio: query.data.value?.ticket_medio ?? 0,
  }));

  return {
    stats,
    isLoading: query.isLoading,
  };
}

export function useOrderServiceQueryByCliente(clienteId: Ref<number | null>) {
  const currentPage = ref(1);

  const query = useQuery({
    queryKey: [ORDER_SERVICE_QUERY_KEY, 'by-cliente', clienteId, currentPage],
    queryFn: () => getOsByClienteId(clienteId.value!, currentPage.value),
    enabled: computed(() => !!clienteId.value && clienteId.value > 0),
    staleTime: ORDER_SERVICE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });

  return {
    items: computed(() => query.data.value?.items ?? []),
    totalPages: computed(() => query.data.value?.total_pages ?? 1),
    totalItems: computed(() => query.data.value?.total_items ?? 0),
    currentPage,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
