import { computed, type Ref } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import {
  getEmployeesAll,
  getCustomersBySearch,
} from '../../../services/relationship/osRelationshipGet.service';

import {
  OS_CUSTOMER_QUERY_KEY,
  OS_CUSTOMER_QUERY_STALE_TIME,
  OS_EMPLOYEE_QUERY_KEY,
  OS_EMPLOYEE_QUERY_STALE_TIME,
  ORDER_SERVICE_REFETCH_INTERVAL,
} from '../../../constants/core.constant';

/**
 * Clientes que casam com o termo digitado no seletor da OS.
 *
 * Uma chave por termo, todas penduradas no prefixo canônico de cliente — é o
 * que mantém `invalidateQueries([CLIENTES_KEY])` alcançando estas caches quando
 * um cliente é criado ou editado.
 *
 * Sem `refetchInterval`: isto é caixa de busca, aberta por segundos enquanto o
 * atendente digita, não painel que precisa acompanhar outro terminal.
 */
export function useOsCustomersSearch(termo: Ref<string>) {
  return useQuery({
    queryKey: computed(() => [...OS_CUSTOMER_QUERY_KEY, termo.value.trim()]),
    queryFn: () => getCustomersBySearch(termo.value),
    enabled: computed(() => termo.value.trim().length > 0),
    staleTime: OS_CUSTOMER_QUERY_STALE_TIME,
  });
}

export function useOsEmployeesGet() {
  return useQuery({
    queryKey: [OS_EMPLOYEE_QUERY_KEY],
    queryFn: getEmployeesAll,
    staleTime: OS_EMPLOYEE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });
}
