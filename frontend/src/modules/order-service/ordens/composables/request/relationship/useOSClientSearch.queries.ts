import { ref, computed, watch } from 'vue';
import type { Ref, ComputedRef } from 'vue';
import { refDebounced } from '@vueuse/core';

import { useOsCustomersSearch, useOsObjetosSearch } from './useOSRelationshipGet.queries';
import type { CustomerUnionReadSchemaDataType } from '../../../schemas/relationship/customer/customer.schema';
import type { ObjetoBuscaItemDataType } from '../../../schemas/relationship/objetoBusca.schema';

/**
 * Busca de cliente do seletor da OS.
 *
 * Quem filtra é o SERVIDOR. Antes a lista vinha inteira (achava-se) e o filtro
 * acontecia aqui com `includes()` — e o que chegava eram só os 20 cadastros mais
 * recentes, porque a rota `/clientes` é paginada e ninguém pedia página nem
 * limite. Cliente antigo não aparecia por mais certo que se digitasse o nome.
 *
 * E aqui NÃO se refiltra o que o servidor devolveu: o motor de lá ignora acento
 * e ordem das palavras, então um `includes()` local jogaria fora justamente os
 * resultados que ele foi buscar ("joao" achando "João").
 */
export function useOSClientSearch(isOpen: Ref<boolean>): {
  searchQuery: Ref<string>;
  clientes: ComputedRef<CustomerUnionReadSchemaDataType[]>;
  objetos: ComputedRef<ObjetoBuscaItemDataType[]>;
  isLoading: Ref<boolean>;
  lastCreatedId: Ref<number | null>;
} {
  const searchQuery = ref('');
  const debouncedQuery = refDebounced(searchQuery, 400);
  const lastCreatedId = ref<number | null>(null);

  const { data, isFetching } = useOsCustomersSearch(debouncedQuery);
  const { data: dataObjetos, isFetching: isFetchingObjetos } = useOsObjetosSearch(debouncedQuery);

  // Resetar pesquisa ao fechar
  watch(isOpen, (open) => {
    if (!open) searchQuery.value = '';
  });

  const clientes = computed<CustomerUnionReadSchemaDataType[]>(() => {
    if (!debouncedQuery.value.trim()) return [];
    return data.value ?? [];
  });

  /**
   * Objetos achados pelo identificador (placa, nº de série, código da arte).
   *
   * Mesma regra da lista de clientes: sem termo, lista vazia — a query fica em
   * cache mas o modal recém-aberto não pode mostrar o resultado da busca
   * anterior.
   */
  const objetos = computed<ObjetoBuscaItemDataType[]>(() => {
    if (!debouncedQuery.value.trim()) return [];
    return dataObjetos.value ?? [];
  });

  /**
   * `isFetching`, não `isLoading`: cada termo é uma chave de cache nova, e
   * `isLoading` só cobre a primeira carga de cada uma. Ao voltar para um termo
   * já visitado a lista revalida em silêncio — com `isLoading` a tela mostraria
   * o resultado antigo como se fosse definitivo.
   *
   * O período entre a tecla e o fim do debounce fica coberto porque o termo
   * debounced ainda é o anterior: a lista mostrada continua coerente com ele.
   */
  /**
   * As duas buscas somadas: enquanto qualquer uma responde, a lista está em
   * carregamento. Mostrar "nenhum resultado" porque a busca de cliente chegou
   * primeiro seria mentir por uma fração de segundo — e o atendente já teria
   * clicado em "Cadastrar novo cliente".
   */
  const isLoading = computed(() => isFetching.value || isFetchingObjetos.value);

  return { searchQuery, clientes, objetos, isLoading, lastCreatedId };
}
