import { computed, type Ref } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import {
  getEmployeesAll,
  getCustomersBySearch,
} from '../../../services/relationship/osRelationshipGet.service';

import { buscarObjetosPorIdentificador } from '../../../services/orderServiceGet.service';

import {
  OS_CUSTOMER_QUERY_KEY,
  OS_CUSTOMER_QUERY_STALE_TIME,
  OS_OBJETO_BUSCA_QUERY_KEY,
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

/**
 * Objetos cujo identificador (placa / nº de série / código da arte) casa com o
 * termo — a outra metade do mesmo seletor.
 *
 * Roda em paralelo com a busca de cliente, pelo mesmo termo: o atendente digita
 * a única informação que tem na mão e o servidor decide o que aquilo é. Só um
 * dos dois costuma responder, então a lista não fica ambígua.
 *
 * O piso de 3 caracteres é só para não disparar requisição a cada tecla — o
 * servidor tem o seu próprio (4, o mesmo do registry) e é ele quem manda.
 */
export function useOsObjetosSearch(termo: Ref<string>) {
  return useQuery({
    queryKey: computed(() => [...OS_OBJETO_BUSCA_QUERY_KEY, termo.value.trim()]),
    queryFn: () => buscarObjetosPorIdentificador(termo.value),
    enabled: computed(() => termo.value.trim().length >= 3),
    staleTime: OS_CUSTOMER_QUERY_STALE_TIME,
  });
}

/**
 * A lista de funcionários que alimenta o seletor de técnico da OS.
 *
 * `ativo` NÃO é conveniência — é o que impede esta query de rodar o dia inteiro
 * em toda tela do sistema. O `OSFormModal` é montado sem condição no
 * `MainLayout`, como todos os modais globais, então este composable rodava no
 * setup dele SEMPRE: no PDV, no cadastro de produto, na tela de relatórios, e
 * numa loja que sequer usa Ordem de Serviço.
 *
 * O estrago aparecia em quem NÃO tem `view_employees`: cada ciclo do
 * `refetchInterval` levava 403, e o retry padrão do TanStack transformava isso
 * em quatro requisições. O console de um balconista fechava com quase cem erros
 * — e erro demais esconde o próximo erro de verdade, que foi exatamente o que
 * aconteceu ao caçar outro problema nesta mesma tela.
 *
 * `retry: false` pela mesma razão de `useTerminaisQuery`: 403 de quem não tem
 * permissão não melhora com repetição.
 */
export function useOsEmployeesGet(ativo?: Ref<boolean>) {
  return useQuery({
    queryKey: [OS_EMPLOYEE_QUERY_KEY],
    queryFn: getEmployeesAll,
    enabled: computed(() => ativo?.value ?? true),
    retry: false,
    staleTime: OS_EMPLOYEE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });
}
