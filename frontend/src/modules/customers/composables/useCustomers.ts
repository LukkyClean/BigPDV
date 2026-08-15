import { ref, computed, watch } from 'vue';

import { useCustomerQueryAll } from './request/useCustomerGet.queries';

import type {
  ClienteFormatted,
  ClienteStatsData,
  CustomersTypes,
} from '../types/clientes.types';

import type { CustomerUnionReadSchemaDataType } from '@/shared/schemas/customer/customer.schema';
import { isCustomerPF } from '@/shared/schemas/customer/customer.schema';
import { getInitials } from '@/shared/utils/string.utils';

// ── Helpers ────────────────────────────────────────────────────────────────

function formatCustomer(customer: CustomerUnionReadSchemaDataType): ClienteFormatted {
  const name = isCustomerPF(customer) ? customer.nome : customer.nome_fantasia;
  const doc = isCustomerPF(customer) ? customer.cpf : customer.cnpj;

  return {
    ...customer,
    displayName: name || 'Sem Nome',
    displayDoc: doc || '',
    displayPhone: customer.celular || customer.telefone || '',
    initial: getInitials(name || ''),
    sortName: (name || '').toLowerCase(),
  } as ClienteFormatted;
}

function calculateStats(customers: CustomerUnionReadSchemaDataType[]): ClienteStatsData {
  return {
    total: customers.length,
    ativos: customers.filter((c) => c.ativo).length,
    pf: customers.filter((c) => c.tipo === 'PF').length,
    pj: customers.filter((c) => c.tipo === 'PJ').length,
  };
}

// ── Composable ─────────────────────────────────────────────────────────────

/**
 * Ao garimpar desativados a página vem cheia: o servidor devolve TODOS (não há
 * modo "só inativos" na rota) e o recorte de inativos acontece aqui. Com a
 * página padrão de 20, quem tem poucos inativos via tela vazia e paginação
 * dizendo que havia mais. 100 é o teto da rota.
 */
const LIMITE_GARIMPO_INATIVOS = 100;

export function useCustomers() {
  const {
    searchQuery,
    customers: rawCustomers,
    onlyActive,
    pageLimit,
    totalPages,
    totalItems,
    currentPage,
    isLoading,
    setPage,
  } = useCustomerQueryAll();

  const activeFilterTipo = ref<CustomersTypes>(null);

  /**
   * O filtro da tela decide o que pedir ao servidor.
   *
   * Antes ele era só local, e "Desativado" procurava inativos numa lista da qual
   * o servidor já tinha removido todos os inativos — não tinha como dar
   * resultado nenhum. Um cliente desativado sumia da interface para sempre, sem
   * caminho de volta.
   */
  watch(
    activeFilterTipo,
    (filtro) => {
      const garimpandoInativos = filtro === 'inactive';
      onlyActive.value = !garimpandoInativos;
      pageLimit.value = garimpandoInativos ? LIMITE_GARIMPO_INATIVOS : undefined;
    },
    { immediate: true },
  );

  const filteredCustomers = computed<ClienteFormatted[]>(() => {
    let result = rawCustomers.value;

    if (activeFilterTipo.value !== null) {
      result = result.filter((c) => {
        if (activeFilterTipo.value === 'active') return c.ativo;
        if (activeFilterTipo.value === 'inactive') return !c.ativo;
        return c.tipo === activeFilterTipo.value;
      });
    }

    return result
      .map(formatCustomer)
      .sort((a, b) => a.sortName.localeCompare(b.sortName, 'pt-BR'));
  });

  const stats = computed<ClienteStatsData>(() => calculateStats(rawCustomers.value));

  return {
    customers: filteredCustomers,
    stats,
    searchQuery,
    activeFilterTipo,
    isLoading,
    currentPage,
    totalPages,
    totalItems,
    setPage,
  };
}
