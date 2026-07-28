// ============================================================================
// COMPONENTE: ProductsSuppliersView (Sistema ERP Produto Motorista - Start Big)
// RESPONSABILIDADE: Dashboard central para alternância entre Estoque e Fornecedores.
// FUNCIONALIDADES: Abas dinâmicas (Tabs), listagem de produtos com cards, 
//                  tabela de fornecedores, filtros de busca e gestão de modals.
// TECNOLOGIAS: Vue 3 (Composition API), Computed States, Lucide Icons, Tailwind.
// ============================================================================
<script setup lang="ts">
import { ref, computed } from 'vue';
import { PackageSearch, Plus, ArrowLeftRight, LayoutGrid } from 'lucide-vue-next';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseTab2 from '@/shared/components/ui/BaseTab2/BaseTab2.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import ProductCard from '@/modules/products/inventory/components/ProductCard.vue';
import ProductModal from '@/modules/products/inventory/components/ProductModal.vue';
import TransacoesEstoquePanel from '@/modules/products/inventory/components/TransacoesEstoquePanel.vue';
import MovimentacaoModal from '@/modules/products/inventory/components/MovimentacaoModal.vue';
import FornecedorTable from '../suppliers/components/FornecedorTable.vue';
import FornecedorStats from '../suppliers/components/FornecedorStats.vue';
import FornecedorFormModal from '../suppliers/components/FornecedorFormModal.vue';

import { correspondeBusca } from '@/shared/utils/busca';
import { FILTER_CONFIG, SORT_FILTER_CONFIG } from '@/modules/products/inventory/constants/product.constants';
import { TAB_OPTIONS } from '@/modules/products/shared/constants/tabs.constants';
import { useProductModal } from '../inventory/composables/useProductModal';
import { useProductsQuery, useToggleProductActiveMutation } from '../inventory/composables/useProductsQuery';
import type { ProdutoRead } from '../inventory/types/products.types';
import { useFornecedorModal } from '../suppliers/composables/useFornecedorModal';
import { useFornecedoresQuery } from '../suppliers/composables/useFornecedoresQuery';
import { useToggleFornecedorAtivoMutation } from '../suppliers/composables/useFornecedoresMutations';
import type { FornecedorReadType } from '../suppliers/schemas/fornecedor.schema';

const { openCreateModal, openEditModal, openViewModal } = useProductModal();
const {
  openCreateModal: openCreateFornecedorModal,
  openEditModal: openEditFornecedorModal,
  openViewModal: openViewFornecedorModal,
} = useFornecedorModal();

import { getImageUrl } from '@/shared/utils/print.utils';

const activeTab = ref('product');
const searchTerm = ref<string | null>('');
const selectedFilter = ref<string | null>(null);
const selectedSort = ref<string | null>(null);
const selectedCategory = ref<string | null>(null);
const isGroupedByCategory = ref(false);
const isTransacoesPanelOpen = ref(false);
const isMovimentacaoModalOpen = ref(false);
const movimentacaoInitialProdutoId = ref<number | undefined>(undefined);
const movimentacaoInitialTipo = ref<'ENTRADA' | 'SAIDA' | undefined>(undefined);

// Fornecedor
const {
  searchQuery: fornecedorSearch,
  activeFilterQuery: fornecedorFilter,
  fornecedores,
  stats: fornecedorStats,
  isLoading: isFornecedoresLoading,
  isError: isFornecedoresError,
} = useFornecedoresQuery();
const toggleFornecedorMutation = useToggleFornecedorAtivoMutation();
const isFornecedorToggleModalOpen = ref(false);
const fornecedorToToggle = ref<FornecedorReadType | null>(null);

const { data: products } = useProductsQuery(searchTerm);
const toggleMutation = useToggleProductActiveMutation();

const localOverrides = ref<Record<number, ProdutoRead>>({});

const mergedProducts = computed(() => {
  const base = products.value || [];
  const overrides = Object.values(localOverrides.value);
  const overridesById = new Map(overrides.map((item) => [item.id, item]));
  const merged = base.map((item) => overridesById.get(item.id) || item);
  const baseIds = new Set(base.map((item) => item.id));
  overrides.forEach((item) => {
    if (!baseIds.has(item.id)) merged.push(item);
  });
  return merged;
});

function normalizarCategoria(cat: string | null | undefined): string {
  const raw = (cat || 'SEM CATEGORIA').trim().toUpperCase();
  return raw;
}

function exibirCategoria(cat: string): string {
  return cat.charAt(0).toUpperCase() + cat.slice(1).toLowerCase();
}

const uniqueCategories = computed(() => {
  const cats = new Set(
    mergedProducts.value.map((p) => normalizarCategoria(p.categoria))
  );
  return Array.from(cats).sort((a, b) => a.localeCompare(b, 'pt-BR'));
});

const categoryFilterConfig = computed(() => {
  const config: Record<string, { label: string; class: string; color: string }> = {};
  for (const cat of uniqueCategories.value) {
    config[cat] = {
      label: cat,
      class: 'bg-violet-50 text-violet-600 border border-violet-200',
      color: 'bg-violet-500',
    };
  }
  return config;
});

const filteredProducts = computed(() => {
  const term = (searchTerm.value || '').trim();
  let list = mergedProducts.value;

  if (term) {
    // Mesmas regras do backend (shared/utils/busca) — se divergirem, este
    // filtro descarta em silêncio o que o servidor já tinha encontrado.
    list = list.filter((product) =>
      correspondeBusca(term, [
        product.nome,
        product.codigo_produto,
        product.codigo_barras,
        product.marca,
        product.categoria,
      ]),
    );
  }

  if (selectedFilter.value === 'active') {
    list = list.filter((product) => product.ativo);
  } else if (selectedFilter.value === 'inactive') {
    list = list.filter((product) => !product.ativo);
  }

  if (selectedCategory.value) {
    list = list.filter(
      (product) => (product.categoria || 'SEM CATEGORIA') === selectedCategory.value
    );
  }

  if (selectedSort.value === 'a-z') {
    list = [...list].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  } else if (selectedSort.value === 'z-a') {
    list = [...list].sort((a, b) => b.nome.localeCompare(a.nome, 'pt-BR'));
  }

  return list;
});

const groupedProducts = computed(() => {
  if (!isGroupedByCategory.value) return null;
  const groups: Record<string, ProdutoRead[]> = {};
  for (const product of filteredProducts.value) {
    const cat = normalizarCategoria(product.categoria);
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(product);
  }
  return Object.fromEntries(
    Object.entries(groups).sort(([a], [b]) => a.localeCompare(b, 'pt-BR'))
  );
});

const isSearchActive = computed(() => (searchTerm.value || '').trim().length > 0);
const isFilterActive = computed(
  () => !!selectedFilter.value || !!selectedSort.value || !!selectedCategory.value || isGroupedByCategory.value
);

const emptyState = computed(() => {
  if (isSearchActive.value || isFilterActive.value) {
    return {
      title: 'Nenhum produto encontrado',
      description: 'Ajuste a busca ou os filtros para ver outros resultados.',
      actionLabel: 'Limpar filtros',
      actionType: 'clear',
    };
  }

  return {
    title: 'Nenhum produto cadastrado',
    description: 'Comece cadastrando seu primeiro produto no catalogo.',
    actionLabel: 'Cadastrar produto',
    actionType: 'create',
  };
});

function getProductById(id: number) {
  return mergedProducts.value.find((product) => product.id === id);
}

function getProductImage(product: ProdutoRead) {
  const primary = product.fotos?.find((foto) => foto.principal);
  if (primary?.url) return primary.url;
  return product.fotos?.[0]?.url || '';
}

function handleAddClick() {
  if (activeTab.value === 'product') {
    openCreateModal();
  } else {
    openCreateFornecedorModal();
  }
}

function handleToggleFornecedor(fornecedor: FornecedorReadType) {
  fornecedorToToggle.value = fornecedor;
  isFornecedorToggleModalOpen.value = true;
}

function handleConfirmFornecedorToggle() {
  if (!fornecedorToToggle.value) return;
  toggleFornecedorMutation.mutate(fornecedorToToggle.value.id, {
    onSuccess: () => {
      isFornecedorToggleModalOpen.value = false;
      fornecedorToToggle.value = null;
    },
  });
}

function handleCloseFornecedorToggleModal() {
  isFornecedorToggleModalOpen.value = false;
  fornecedorToToggle.value = null;
}

function handleViewProduct(id: number) {
  const product = getProductById(id);
  if (product) openViewModal(product);
}

function handleEditProduct(id: number) {
  const product = getProductById(id);
  if (product) openEditModal(product);
}

function handleToggleProduct(id: number) {
  toggleMutation.mutate(id, {
    onSuccess: (data) => {
      localOverrides.value = {
        ...localOverrides.value,
        [data.id]: data,
      };
    },
  });
}

function handleEntrada(id: number) {
  movimentacaoInitialProdutoId.value = id;
  movimentacaoInitialTipo.value = 'ENTRADA';
  isMovimentacaoModalOpen.value = true;
}

function handleSaida(id: number) {
  movimentacaoInitialProdutoId.value = id;
  movimentacaoInitialTipo.value = 'SAIDA';
  isMovimentacaoModalOpen.value = true;
}

function handleEmptyAction() {
  if (emptyState.value.actionType === 'clear') {
    searchTerm.value = '';
    selectedFilter.value = null;
    selectedSort.value = null;
    selectedCategory.value = null;
    isGroupedByCategory.value = false;
    return;
  }

  handleAddClick();
}
</script>

<template>
  <div class="p-4 md:p-6 lg:p-8 space-y-6 md:space-y-8">
    <div class="flex flex-col flex-wrap sm:flex-row sm:justify-between sm:items-end gap-4">
      <PageReview
        :title="activeTab === 'product' ? 'Estoque' : 'Fornecedores'"
        :description="activeTab === 'product' ? 'Gerencia os produtos no seu estoque' : 'Gerencie os fornecedores da sua empresa'"
      />

      <div class="flex gap-5">
        <BaseTab2 :options="TAB_OPTIONS" v-model="activeTab" />
        <BaseButton
          variant="primary"
          size="md"
          type="button"
          class="flex gap-1"
          @click="handleAddClick"
        >
          <Plus :size="20" />
          {{ activeTab === 'product' ? 'Adicionar Produto' : 'Adicionar Fornecedor' }}
        </BaseButton>
      </div>
    </div>

    <!-- Produtos Tab -->
    <template v-if="activeTab === 'product'">
      <div class="flex flex-wrap gap-3 p-4 bg-white rounded-2xl">
        <BaseSearchInput
          class="md:max-w-2/3 lg:max-w-1/2"
          v-model="searchTerm"
          placeholder="Buscar produto por nome ou código..."
        />
        <BaseFilter :filter-config="FILTER_CONFIG" v-model="selectedFilter" />
        <BaseFilter
          :filter-config="SORT_FILTER_CONFIG"
          v-model="selectedSort"
          title="Ordenar por Nome"
          button-label="Ordenar"
        />
        <BaseFilter
          :filter-config="categoryFilterConfig"
          v-model="selectedCategory"
          title="Filtrar por Categoria"
          button-label="Categoria"
        />
        <button
          :class="[
            'flex items-center gap-2 px-4 py-2 rounded-lg text-xs md:text-sm font-semibold border transition-all cursor-pointer select-none',
            isGroupedByCategory
              ? 'bg-brand-primary/10 text-brand-primary border-brand-primary'
              : 'text-zinc-600 border-brand-grey hover:text-brand-primary/80 hover:border-brand-primary/80',
          ]"
          @click="isGroupedByCategory = !isGroupedByCategory"
        >
          <LayoutGrid :size="16" />
          Agrupar
        </button>
        <button
          class="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl border border-zinc-200 text-sm font-medium text-zinc-600 hover:bg-zinc-50 hover:border-zinc-300 transition-colors cursor-pointer shrink-0"
          @click="isTransacoesPanelOpen = true"
        >
          <ArrowLeftRight :size="16" />
          Transações
        </button>
      </div>

      <!-- Agrupado por categoria -->
      <template v-if="isGroupedByCategory && groupedProducts">
        <div v-for="(products, category) in groupedProducts" :key="category" class="space-y-4">
          <h2 class="text-lg font-bold text-zinc-700 border-b border-zinc-200 pb-2">
            {{ exibirCategoria(String(category)) }}
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <ProductCard
              v-for="product in products"
              :key="product.id"
              :id="product.id"
              :name="product.nome"
              :description="product.observacao || 'Sem descrição cadastrada'"
              :category="product.categoria || 'SEM CATEGORIA'"
              :price="product.estoque.valor_varejo / 100"
              :storage="product.estoque.quantidade || 0"
              :image_url="getImageUrl(getProductImage(product)) ?? ''"
              :status="product.ativo"
              @view="handleViewProduct"
              @edit="handleEditProduct"
              @toggle="handleToggleProduct"
              @entrada="handleEntrada"
              @saida="handleSaida"
            />
          </div>
        </div>
      </template>

      <!-- Lista plana (padrão) -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <ProductCard
          v-for="product in filteredProducts"
          :key="product.id"
          :id="product.id"
          :name="product.nome"
          :description="product.observacao || 'Sem descrição cadastrada'"
          :category="product.categoria || 'SEM CATEGORIA'"
          :price="product.estoque.valor_varejo / 100"
          :storage="product.estoque.quantidade || 0"
          :image_url="getImageUrl(getProductImage(product)) ?? ''"
          :status="product.ativo"
          @view="handleViewProduct"
          @edit="handleEditProduct"
          @toggle="handleToggleProduct"
          @entrada="handleEntrada"
          @saida="handleSaida"
        />
      </div>

      <div
        v-if="filteredProducts.length === 0"
        class="rounded-2xl border border-dashed border-zinc-200 bg-white p-10 text-center"
      >
        <div
          class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-primary/10 text-brand-primary"
        >
          <PackageSearch :size="28" />
        </div>
        <h3 class="text-base font-semibold text-zinc-800">{{ emptyState.title }}</h3>
        <p class="mt-1 text-sm text-zinc-400">{{ emptyState.description }}</p>
        <div class="mt-6 flex items-center justify-center">
          <BaseButton
            variant="primary"
            size="md"
            type="button"
            class="flex items-center gap-2"
            @click="handleEmptyAction"
          >
            <Plus v-if="emptyState.actionType === 'create'" :size="18" />
            {{ emptyState.actionLabel }}
          </BaseButton>
        </div>
      </div>
    </template>

    <!-- Fornecedores Tab -->
    <template v-else-if="activeTab === 'supplier'">
      <FornecedorStats
        :total="fornecedorStats.total"
        :ativos="fornecedorStats.ativos"
        :inativos="fornecedorStats.inativos"
:loading="isFornecedoresLoading"
      />

      <FornecedorTable
        :fornecedores="fornecedores"
        :is-loading="isFornecedoresLoading"
        :is-error="isFornecedoresError"
        v-model:search="fornecedorSearch"
        v-model:status-filter="fornecedorFilter"
        @view="openViewFornecedorModal"
        @edit="openEditFornecedorModal"
        @toggle-status="handleToggleFornecedor"
      />
    </template>

    <ProductModal />
    <FornecedorFormModal />

    <TransacoesEstoquePanel
      :is-open="isTransacoesPanelOpen"
      :produtos="mergedProducts"
      @close="isTransacoesPanelOpen = false"
    />

    <MovimentacaoModal
      :is-open="isMovimentacaoModalOpen"
      :produtos="mergedProducts"
      :initial-produto-id="movimentacaoInitialProdutoId"
      :initial-tipo="movimentacaoInitialTipo"
      @close="isMovimentacaoModalOpen = false"
    />

    <BaseConfirmModal
      :is-open="isFornecedorToggleModalOpen"
      :title="(fornecedorToToggle?.ativo ? 'Desativar' : 'Ativar') + ' Fornecedor?'"
      :description="`Deseja realmente ${fornecedorToToggle?.ativo ? 'desativar' : 'ativar'} o fornecedor ${fornecedorToToggle?.nome}?`"
      :confirm-label="fornecedorToToggle?.ativo ? 'Desativar' : 'Ativar'"
      :variant="fornecedorToToggle?.ativo ? 'danger' : 'info'"
      @close="handleCloseFornecedorToggleModal"
      @confirm="handleConfirmFornecedorToggle"
    />
  </div>
</template>
