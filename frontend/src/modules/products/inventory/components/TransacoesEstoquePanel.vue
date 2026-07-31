// ============================================================================
// COMPONENTE: HistoricoMovimentacoesDrawer
// PROJETO: Start Big - Gestão de Hardware & ERP
// RESPONSABILIDADE: Exibir o histórico cronológico de transações do estoque.
// FUNCIONALIDADES: 
//   - Filtros dinâmicos por tipo (Entrada/Saída/Ajuste) e busca textual.
//   - Paginação do lado do cliente (Client-side pagination).
//   - Estados de Loading (Skeleton Screen) e Empty States (Busca sem resultado).
//   - Formatação de data brasileira e indicadores visuais de saldo posterior.
// ============================================================================
<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { X, Plus, ArrowDownCircle, ArrowUpCircle, SlidersHorizontal, PackageSearch, Search, Pencil } from 'lucide-vue-next';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';
import type { FilterOption } from '@/shared/types/filter.types';
import BasePagination from '@/shared/components/commons/BasePagination/BasePagination.vue';
import MovimentacaoModal from './MovimentacaoModal.vue';
import { useMovimentacoesQuery } from '../composables/useMovimentacoesQuery';
import { formatCurrency } from '@/shared/utils/finance';
import type { ProdutoRead } from '../types/products.types';

interface Props {
  isOpen: boolean;
  produtos: ProdutoRead[];
}

defineProps<Props>();
const emit = defineEmits<{ (e: 'close'): void }>();

const isMovimentacaoModalOpen = ref(false);
const searchTerm = ref('');
const tipoFilter = ref<string | null>(null);
const currentPage = ref(1);
const ITEMS_PER_PAGE = 10;

const { data: movimentacoes, isLoading } = useMovimentacoesQuery();

const TIPO_FILTER_CONFIG: Record<string, FilterOption> = {
  ENTRADA: { label: 'Entrada', color: 'bg-brand-primary', class: 'bg-brand-primary/10 text-brand-primary border border-brand-primary/30' },
  SAIDA: { label: 'Saída', color: 'bg-red-500', class: 'bg-red-50 text-red-600 border border-red-200' },
  AJUSTE: { label: 'Ajuste', color: 'bg-amber-500', class: 'bg-amber-50 text-amber-600 border border-amber-200' },
  EDICAO_DADOS: { label: 'Edição', color: 'bg-violet-500', class: 'bg-violet-50 text-violet-600 border border-violet-200' },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const tipoConfig: Record<string, { icon: any; label: string; class: string }> = {
  ENTRADA: { icon: ArrowDownCircle, label: 'Entrada', class: 'text-brand-primary bg-brand-primary/10 border-brand-primary/30' },
  SAIDA: { icon: ArrowUpCircle, label: 'Saída', class: 'text-red-600 bg-red-50 border-red-200' },
  AJUSTE: { icon: SlidersHorizontal, label: 'Ajuste', class: 'text-amber-600 bg-amber-50 border-amber-200' },
  EDICAO_DADOS: { icon: Pencil, label: 'Edição', class: 'text-violet-600 bg-violet-50 border-violet-200' },
};

const filteredMovimentacoes = computed(() => {
  let list = movimentacoes.value ?? [];

  const term = searchTerm.value.trim().toLowerCase();
  if (term) {
    list = list.filter(
      (m) =>
        m.produto_nome.toLowerCase().includes(term) ||
        m.usuario_nome.toLowerCase().includes(term) ||
        (m.observacao ?? '').toLowerCase().includes(term),
    );
  }

  if (tipoFilter.value) {
    list = list.filter((m) => m.tipo === tipoFilter.value);
  }

  return list;
});

const totalItems = computed(() => filteredMovimentacoes.value.length);
const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / ITEMS_PER_PAGE)));

const pagedMovimentacoes = computed(() => {
  const start = (currentPage.value - 1) * ITEMS_PER_PAGE;
  return filteredMovimentacoes.value.slice(start, start + ITEMS_PER_PAGE);
});

watch([searchTerm, tipoFilter], () => {
  currentPage.value = 1;
});

function formatDate(isoString: string) {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(isoString));
}

function quantidadeLabel(tipo: string, qtd: number) {
  if (tipo === 'ENTRADA') return `+${qtd}`;
  if (tipo === 'SAIDA') return `-${qtd}`;
  if (tipo === 'EDICAO_DADOS') return '—';
  return `=${qtd}`;
}

function quantidadeClass(tipo: string) {
  if (tipo === 'ENTRADA') return 'text-brand-primary font-bold';
  if (tipo === 'SAIDA') return 'text-red-600 font-bold';
  if (tipo === 'EDICAO_DADOS') return 'text-violet-600 font-bold';
  return 'text-amber-600 font-bold';
}
</script>

<template>
  <!-- Overlay -->
  <Teleport to="body">
    <Transition name="panel">
      <div v-if="isOpen" class="fixed inset-0 z-40 flex justify-end">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/30 backdrop-blur-sm"
          @click="emit('close')"
        />

        <!-- Drawer panel -->
        <div class="relative z-50 w-full max-w-lg bg-white shadow-2xl flex flex-col h-full">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100 shrink-0">
            <div>
              <h2 class="text-lg font-semibold text-zinc-800">Transações de Estoque</h2>
              <p class="text-xs text-zinc-400 mt-0.5">Histórico de entradas, saídas e ajustes</p>
            </div>
            <div class="flex items-center gap-2">
              <BaseButton
                type="button"
                variant="primary"
                size="sm"
                class="flex items-center gap-1"
                @click="isMovimentacaoModalOpen = true"
              >
                <Plus :size="15" />
                Nova
              </BaseButton>
              <button
                class="p-2 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors cursor-pointer"
                @click="emit('close')"
              >
                <X :size="20" />
              </button>
            </div>
          </div>

          <!-- Search + Filter bar -->
          <div class="flex items-center gap-2 px-6 py-3 border-b border-zinc-100 shrink-0">
            <div class="relative flex-1">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" :size="15" />
              <input
                v-model="searchTerm"
                type="text"
                placeholder="Buscar por produto, usuário, observação..."
                class="w-full pl-9 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-zinc-50 placeholder-zinc-400 focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
              />
            </div>
            <BaseFilter :filter-config="TIPO_FILTER_CONFIG" v-model="tipoFilter" />
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-y-auto px-6 py-4">
            <!-- Loading -->
            <div v-if="isLoading" class="space-y-3">
              <div
                v-for="i in 5"
                :key="i"
                class="h-20 bg-zinc-100 rounded-xl animate-pulse"
              />
            </div>

            <!-- Empty: sem registros no banco -->
            <div
              v-else-if="!movimentacoes?.length"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <div class="w-14 h-14 bg-zinc-100 rounded-2xl flex items-center justify-center mb-4 text-zinc-400">
                <PackageSearch :size="26" />
              </div>
              <p class="text-sm font-medium text-zinc-600">Nenhuma movimentação registrada</p>
              <p class="text-xs text-zinc-400 mt-1">Registre a primeira entrada ou saída de estoque</p>
            </div>

            <!-- Empty: filtro sem resultado -->
            <div
              v-else-if="!filteredMovimentacoes.length"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <div class="w-14 h-14 bg-zinc-100 rounded-2xl flex items-center justify-center mb-4 text-zinc-400">
                <Search :size="26" />
              </div>
              <p class="text-sm font-medium text-zinc-600">Nenhum resultado encontrado</p>
              <p class="text-xs text-zinc-400 mt-1">Tente ajustar a busca ou o filtro</p>
            </div>

            <!-- List -->
            <div v-else class="space-y-3">
              <div
                v-for="mov in pagedMovimentacoes"
                :key="mov.id"
                class="bg-white border border-zinc-100 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <div class="flex items-start justify-between gap-3">
                  <!-- Left: tipo badge + produto -->
                  <div class="flex items-start gap-3 min-w-0">
                    <span
                      class="flex items-center gap-1 px-2 py-1 rounded-lg border text-xs font-semibold shrink-0"
                      :class="tipoConfig[mov.tipo].class"
                    >
                      <component :is="tipoConfig[mov.tipo].icon" :size="12" />
                      {{ tipoConfig[mov.tipo].label }}
                    </span>
                    <div class="min-w-0">
                      <p class="text-sm font-semibold text-zinc-800 truncate">{{ mov.produto_nome }}</p>
                      <p class="text-xs text-zinc-400 mt-0.5">{{ mov.usuario_nome }}</p>
                    </div>
                  </div>

                  <!-- Right: quantidade -->
                  <div class="text-right shrink-0">
                    <p class="text-base" :class="quantidadeClass(mov.tipo)">
                      {{ quantidadeLabel(mov.tipo, mov.quantidade) }}
                      <span v-if="mov.tipo !== 'EDICAO_DADOS'"> un</span>
                    </p>
                    <p v-if="mov.tipo !== 'EDICAO_DADOS'" class="text-xs text-zinc-400">→ {{ mov.quantidade_posterior }} un</p>
                    <!--
                      Custo congelado nesta linha. É a trilha de auditoria do
                      lucro: dá para conferir, movimento a movimento, com que
                      custo cada peça entrou ou saiu — mesmo anos depois, e
                      mesmo que o preço do fornecedor tenha mudado várias vezes.
                    -->
                    <p v-if="mov.custo_unitario != null" class="text-xs text-zinc-400 mt-0.5">
                      {{ formatCurrency(mov.custo_unitario) }}/un
                    </p>
                  </div>
                </div>

                <!-- Observação -->
                <p v-if="mov.observacao" class="mt-2 text-xs text-zinc-500 italic line-clamp-2">
                  "{{ mov.observacao }}"
                </p>

                <!-- Data -->
                <p class="mt-2 text-xs text-zinc-300">{{ formatDate(mov.created_at) }}</p>
              </div>
            </div>
          </div>

          <!-- Paginação -->
          <div v-if="!isLoading && filteredMovimentacoes.length > 0" class="shrink-0 border-t border-zinc-100">
            <BasePagination
              :current-page="currentPage"
              :total-pages="totalPages"
              :total-items="totalItems"
              item-label="movimentação"
              item-label-plural="movimentações"
              @update:current-page="currentPage = $event"
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <MovimentacaoModal
    :is-open="isMovimentacaoModalOpen"
    :produtos="produtos"
    @close="isMovimentacaoModalOpen = false"
  />
</template>

<style scoped>
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.2s ease;
}
.panel-enter-from,
.panel-leave-to {
  opacity: 0;
}
.panel-enter-active > div:last-child,
.panel-leave-active > div:last-child {
  transition: transform 0.25s ease;
}
.panel-enter-from > div:last-child,
.panel-leave-to > div:last-child {
  transform: translateX(100%);
}
</style>
