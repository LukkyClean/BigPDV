<script setup lang="ts">
import { computed, toRef } from 'vue';
import { ArrowDownToLine } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { getStatusLabel, getStatusColor } from '../../../shared/utils/formatters';
import { useOrderServiceQueryByCliente } from '../../composables/request/useOrderServiceGet.queries';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';

interface Props {
  isOpen: boolean;
  clienteId: number | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  reutilizarObjeto: [os: OrderServiceReadDataType];
}>();

const clienteIdRef = toRef(() => props.clienteId);
const { items, totalPages, totalItems, currentPage, isLoading, isError } =
  useOrderServiceQueryByCliente(clienteIdRef);

const isEmpty = computed(() => !isLoading.value && items.value.length === 0);

function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function getObjetoLabel(os: OrderServiceReadDataType): string {
  const objeto = os.objeto;
  const parts = [objeto.tipo_equipamento, objeto.marca, objeto.modelo].filter(Boolean);
  return parts.join(' · ') || '-';
}

function truncate(text: string | null | undefined, maxLength: number): string {
  if (!text) return '-';
  return text.length > maxLength ? text.slice(0, maxLength) + '…' : text;
}

const statusColorMap: Record<string, string> = {
  blue: 'bg-brand-primary-light text-brand-primary',
  yellow: 'bg-yellow-50 text-yellow-700',
  orange: 'bg-orange-50 text-orange-700',
  purple: 'bg-purple-50 text-purple-700',
  indigo: 'bg-indigo-50 text-indigo-700',
  green: 'bg-emerald-50 text-emerald-700',
  red: 'bg-red-50 text-red-700',
  gray: 'bg-zinc-50 text-zinc-700',
};

function getStatusClass(status: string): string {
  return statusColorMap[getStatusColor(status as Parameters<typeof getStatusColor>[0])] || statusColorMap.gray;
}
</script>

<template>
  <BaseModal
    :is-open="props.isOpen"
    title="Histórico de OS do Cliente"
    size="3xl"
    @close="emit('close')"
  >
    <BaseTableContainer
      :is-loading="isLoading"
      :is-error="isError"
      :is-empty="isEmpty"
      :current-page="currentPage"
      :total-pages="totalPages"
      :total-items="totalItems"
      item-label="ordem de serviço"
      item-label-plural="ordens de serviço"
      empty-title="Nenhuma OS encontrada"
      empty-description="Este cliente ainda não possui ordens de serviço registradas."
      error-title="Erro ao carregar histórico"
      error-description="Não foi possível buscar o histórico de OS deste cliente."
      @update:current-page="(page: number) => (currentPage = page)"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-200 text-left">
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Nº OS</th>
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Data</th>
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Objeto</th>
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Defeito</th>
            <th class="px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Ação</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr
            v-for="os in items"
            :key="os.id"
            class="hover:bg-slate-50 transition-colors"
          >
            <td class="px-4 py-3 font-semibold text-slate-800 whitespace-nowrap">
              {{ os.numero_os }}
            </td>
            <td class="px-4 py-3 text-slate-600 whitespace-nowrap">
              {{ formatDate(os.data_criacao) }}
            </td>
            <td class="px-4 py-3">
              <span
                :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide', getStatusClass(os.status)]"
              >
                {{ getStatusLabel(os.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-slate-600">
              {{ getObjetoLabel(os) }}
            </td>
            <td class="px-4 py-3 text-slate-500 max-w-50">
              {{ truncate(os.defeito_relatado, 50) }}
            </td>
            <td class="px-4 py-3 text-right">
              <BaseButton
                variant="ghost"
                size="sm"
                @click="emit('reutilizarObjeto', os)"
              >
                <ArrowDownToLine :size="14" class="mr-1" />
                Reutilizar
              </BaseButton>
            </td>
          </tr>
        </tbody>
      </table>
    </BaseTableContainer>
  </BaseModal>
</template>
