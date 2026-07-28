<script setup lang="ts">
import { Ellipsis, Pencil, CheckCircle, XCircle, RotateCcw, Printer } from 'lucide-vue-next';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import { OS_STATUS_FILTER_CONFIG } from '../constants/ordemServico.constants';
import { getStatusLabel, getClienteNome } from '../../shared/utils/formatters';
import { formatCurrency } from '@/shared/utils/finance';
import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';

interface Props {
  ordensServico: OrderServiceReadDataType[];
  isLoading?: boolean;
  totalPages?: number;
  currentPage?: number;
  totalItems?: number;
}

withDefaults(defineProps<Props>(), {
  isLoading: false,
  totalPages: 1,
  currentPage: 1,
  totalItems: 0,
});

const emit = defineEmits<{
  view: [os: OrderServiceReadDataType];
  edit: [os: OrderServiceReadDataType];
  finalizar: [os: OrderServiceReadDataType];
  cancelar: [os: OrderServiceReadDataType];
  reabrir: [os: OrderServiceReadDataType];
  print: [os: OrderServiceReadDataType];
  'update:currentPage': [page: number];
}>();

const search = defineModel<string>('search', { default: '' });
const activeFilter = defineModel<string | null>('activeFilter', { default: null });

function formatDate(dateValue: string | Date): string {
  return new Date(dateValue).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
  });
}

function getStatusConfig(status: string) {
  const configs: Record<string, { bg: string; text: string }> = {
    ABERTA:               { bg: 'bg-blue-50',    text: 'text-blue-600'    },
    EM_ANDAMENTO:         { bg: 'bg-amber-50',   text: 'text-amber-700'   },
    AGUARDANDO_PECAS:     { bg: 'bg-orange-50',  text: 'text-orange-700'  },
    AGUARDANDO_APROVACAO: { bg: 'bg-purple-50',  text: 'text-purple-700'  },
    AGUARDANDO_RETIRADA:  { bg: 'bg-indigo-50',  text: 'text-indigo-700'  },
    FINALIZADA:           { bg: 'bg-emerald-50', text: 'text-emerald-700' },
    CANCELADA:            { bg: 'bg-red-50',     text: 'text-red-700'     },
  };
  return configs[status] || { bg: 'bg-zinc-50', text: 'text-zinc-700' };
}

function getOSSequence(numero_os: string): string {
  if (!numero_os) return '00';
  const parts = numero_os.split('-');
  if (parts.length === 3) {
    const seq = parseInt(parts[2], 10);
    return String(seq).padStart(2, '0');
  }
  return '00';
}
</script>

<template>
  <BaseTableContainer
    :is-loading="isLoading"
    :is-empty="ordensServico.length === 0"
    :current-page="currentPage"
    :total-pages="totalPages"
    :total-items="totalItems"
    item-label="OS"
    item-label-plural="OS"
    empty-title="Nenhuma OS encontrada"
    empty-description='Clique em "Nova OS" para criar uma ordem de servico'
    @update:current-page="emit('update:currentPage', $event)"
  >
    <template #toolbar>
      <BaseSearchInput v-model="search" placeholder="Buscar por número, cliente..." />
      <BaseFilter v-model="activeFilter" :filter-config="OS_STATUS_FILTER_CONFIG" button-label="Filtros" />
    </template>

    <div class="overflow-x-auto">
      <table class="w-full text-left min-w-160">
        <thead>
          <tr class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100">
            <th class="px-4 md:px-6 py-3 md:py-4">OS</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Cliente / Objeto</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Status</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Data</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Valor</th>
            <th class="px-4 md:px-6 py-3 md:py-4 text-right min-w-40">Ações Rápidas</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr
            v-for="os in ordensServico"
            :key="os.id"
            class="hover:bg-zinc-50/50 transition-colors group cursor-pointer"
            @click="emit('view', os)"
          >
            <td class="px-4 md:px-6 py-3 md:py-4">
              <div class="w-10 h-10 bg-brand-primary/10 rounded-xl flex flex-col items-center justify-center text-brand-primary">
                <span class="text-[7px] opacity-70 font-medium leading-none">OS</span>
                <span class="text-sm font-bold leading-none mt-0.5">{{ getOSSequence(os.numero_os) }}</span>
              </div>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4">
              <div class="flex flex-col">
                <span class="text-sm font-semibold text-zinc-900 group-hover:text-brand-primary transition-colors">
                  {{ getClienteNome(os.cliente) }}
                </span>
                <span class="text-[10px] text-zinc-400 mt-0.5">{{ os.objeto.tipo_equipamento }}</span>
              </div>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4">
              <span
                :class="[
                  'px-2 md:px-3 py-1 rounded-full text-[10px] md:text-[11px] font-bold whitespace-nowrap',
                  getStatusConfig(os.status).bg,
                  getStatusConfig(os.status).text,
                ]"
              >
                {{ getStatusLabel(os.status) }}
              </span>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors">
              {{ formatDate(os.data_criacao) }}
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors">
              <span v-if="os.valor_total > 0">{{ formatCurrency(os.valor_total) }}</span>
              <span v-else class="text-zinc-300">—</span>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4 max-w-36">
              <div class="flex items-center justify-end h-full">
                <div class="hidden group-hover:flex items-center justify-end gap-1 transition-all duration-200">
                  <template v-if="os.status !== 'FINALIZADA' && os.status !== 'CANCELADA'">
                    <button
                      type="button"
                      title="Imprimir OS"
                      class="p-2 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/10 transition-colors cursor-pointer"
                      @click.stop="emit('print', os)"
                    >
                      <Printer :size="18" />
                    </button>
                    <button
                      type="button"
                      title="Editar"
                      class="p-2 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/10 transition-colors cursor-pointer"
                      @click.stop="emit('edit', os)"
                    >
                      <Pencil :size="18" />
                    </button>
                    <button
                      type="button"
                      title="Finalizar OS"
                      class="p-2 rounded-lg text-zinc-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors cursor-pointer"
                      @click.stop="emit('finalizar', os)"
                    >
                      <CheckCircle :size="18" />
                    </button>
                    <button
                      type="button"
                      title="Cancelar OS"
                      class="p-2 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                      @click.stop="emit('cancelar', os)"
                    >
                      <XCircle :size="18" />
                    </button>
                  </template>
                  <template v-else>
                    <button
                      type="button"
                      title="Reabrir OS"
                      class="p-2 rounded-lg text-zinc-400 hover:text-amber-600 hover:bg-amber-50 transition-colors cursor-pointer"
                      @click.stop="emit('reabrir', os)"
                    >
                      <RotateCcw :size="18" />
                    </button>
                    <button
                      type="button"
                      title="Imprimir OS"
                      class="p-2 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/10 transition-colors cursor-pointer"
                      @click.stop="emit('print', os)"
                    >
                      <Printer :size="18" />
                    </button>
                  </template>
                </div>
                <div class="p-2 text-zinc-400 group-hover:hidden cursor-pointer">
                  <Ellipsis :size="20" />
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseTableContainer>
</template>
