<script setup lang="ts">
/**
 * ===========================================================================
 * COMPONENTE: BaseTableContainer
 * DESCRICAO: Container padrao para tabelas do sistema com toolbar e paginacao
 * ===========================================================================
 *
 * SLOTS:
 * - toolbar: Conteudo da barra de ferramentas (busca, filtros)
 * - default: Conteudo da tabela
 * - empty: Estado vazio customizado
 * - loading: Estado de loading customizado
 * - error: Estado de erro customizado
 *
 * USO:
 * <BaseTableContainer
 *   :is-loading="isLoading"
 *   :is-error="isError"
 *   :is-empty="items.length === 0"
 *   :current-page="currentPage"
 *   :total-pages="totalPages"
 *   :total-items="totalItems"
 *   item-label="cliente"
 *   empty-title="Nenhum cliente encontrado"
 *   empty-description="Clique em 'Novo Cliente' para cadastrar"
 *   @update:current-page="setPage"
 * >
 *   <template #toolbar>
 *     <SearchInput ... />
 *     <FilterDropdown ... />
 *   </template>
 *
 *   <table>...</table>
 * </BaseTableContainer>
 * ===========================================================================
 */

import { Search, AlertCircle } from 'lucide-vue-next';
import BasePagination from '../BasePagination/BasePagination.vue';

interface Props {
  isLoading?: boolean;
  isError?: boolean;
  isEmpty?: boolean;
  // Paginação
  currentPage?: number;
  totalPages?: number;
  totalItems?: number;
  itemLabel?: string;
  itemLabelPlural?: string;
  // Empty State
  emptyTitle?: string;
  emptyDescription?: string;
  // Error State
  errorTitle?: string;
  errorDescription?: string;
}

withDefaults(defineProps<Props>(), {
  isLoading: false,
  isError: false,
  isEmpty: false,
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  itemLabel: 'registro',
  itemLabelPlural: '',
  emptyTitle: 'Nenhum registro encontrado',
  emptyDescription: '',
  errorTitle: 'Erro ao carregar dados',
  errorDescription: 'Verifique sua conexão e tente novamente.',
});

const emit = defineEmits<{
  'update:currentPage': [page: number];
}>();
</script>

<template>
  <div class="bg-white border border-zinc-200 rounded-2xl md:rounded-3xl shadow-sm flex flex-col h-full">
    <!-- Toolbar -->
    <div
      v-if="$slots.toolbar"
      class="p-4 md:p-6 md:max-w-2/3 lg:max-w-2/3 border-b border-zinc-100 flex gap-4 items-center"
    >
      <slot name="toolbar" />
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex-1 p-8">
      <slot name="loading">
        <div class="space-y-4">
          <div
            v-for="i in 5"
            :key="i"
            class="flex items-center gap-4 animate-pulse"
          >
            <div class="w-10 h-10 bg-zinc-200 rounded-full"></div>
            <div class="flex-1 space-y-2">
              <div class="h-4 bg-zinc-200 rounded w-1/3"></div>
              <div class="h-3 bg-zinc-100 rounded w-1/4"></div>
            </div>
            <div class="h-6 bg-zinc-200 rounded-full w-16"></div>
          </div>
        </div>
      </slot>
    </div>

    <!-- Error State -->
    <div
      v-else-if="isError"
      class="flex-1 p-8 text-center text-red-500 flex flex-col items-center gap-2"
    >
      <slot name="error">
        <AlertCircle :size="32" />
        <p class="text-sm">{{ errorTitle }}</p>
        <p class="text-xs text-zinc-400">{{ errorDescription }}</p>
      </slot>
    </div>

    <!-- Empty State -->
    <div v-else-if="isEmpty" class="flex-1 flex items-center justify-center py-12">
      <slot name="empty">
        <div class="flex flex-col items-center gap-2 text-center px-4">
          <div class="w-12 h-12 bg-zinc-100 rounded-full flex items-center justify-center mb-2">
            <Search :size="24" class="text-zinc-300" />
          </div>
          <span class="text-sm font-medium text-zinc-500">{{ emptyTitle }}</span>
          <span v-if="emptyDescription" class="text-xs text-zinc-400">{{ emptyDescription }}</span>
        </div>
      </slot>
    </div>

    <!-- Content -->
    <div v-else class="flex-1 overflow-auto">
      <slot />
    </div>

    <!-- Pagination Footer -->
    <BasePagination
      v-if="!isLoading && !isError && !isEmpty && totalItems > 0"
      :current-page="currentPage"
      :total-pages="totalPages"
      :total-items="totalItems"
      :item-label="itemLabel"
      :item-label-plural="itemLabelPlural"
      @update:current-page="emit('update:currentPage', $event)"
    />
  </div>
</template>
