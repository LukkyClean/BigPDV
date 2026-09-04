import { ref, computed, watch } from 'vue';
import { refDebounced } from '@vueuse/core';

import { useSalesListQuery } from '../queries/useSalesListQuery';

export function useSaleTable() {
  const searchTerm = ref<string | null>(null);
  const debouncedSearchTerm = refDebounced(searchTerm, 300);
  const activeFilter = ref<'FINALIZADA' | 'CANCELADA' | 'ATIVA' | 'NO_CAIXA' | null>(null);
  const page = ref<number>(1);

  watch([searchTerm, activeFilter], () => {
    page.value = 1;
  });

  const filters = computed(() => {
    const busca = debouncedSearchTerm.value ? { search: debouncedSearchTerm.value } : {};

    // 'NO_CAIXA' não é um status — é a fila, que no banco é coluna à parte.
    // Vira `na_fila`, e a venda continua ATIVA. Mandá-lo como `status` faria o
    // backend procurar um valor de enum que não existe.
    if (activeFilter.value === 'NO_CAIXA') {
      return { ...busca, na_fila: true };
    }

    return {
      ...busca,
      ...(activeFilter.value && { status: activeFilter.value }),
    };
  });

  const goToPage = (newPage: number) => {
    page.value = newPage;
  };

  const { data: sales, isLoading } = useSalesListQuery(filters, page);

  return {
    searchTerm,
    activeFilter,
    goToPage,
    sales,
    isLoading,
  };
}
