<script setup lang="ts">
import { ShoppingBag } from 'lucide-vue-next';
import { formatCurrency } from '@/shared/utils/finance';
import { useSaleModal } from '@/modules/sales/composables/flows/useSaleModal';
import type { UltimaVendaItemData } from '../../schemas/dashboard.schema';
import { formatHora } from '@/shared/utils/date.utils';

interface Props {
  vendas: UltimaVendaItemData[];
  isLoading: boolean;
  isError: boolean;
  showTime?: boolean;
}

defineProps<Props>();

const { openSaleEditModal, openSaleViewModal } = useSaleModal();

function handleRowClick(venda: UltimaVendaItemData) {
  if (venda.status === 'ATIVA') {
    openSaleEditModal(venda.id);
  } else {
    openSaleViewModal(venda.id);
  }
}

const statusConfig: Record<string, { label: string; class: string }> = {
  ATIVA: {
    label: 'Ativa',
    class: 'bg-blue-50 text-blue-600 border border-blue-200',
  },
  FINALIZADA: {
    label: 'Finalizada',
    class: 'bg-emerald-50 text-emerald-600 border border-emerald-200',
  },
  CANCELADA: {
    label: 'Cancelada',
    class: 'bg-red-50 text-red-600 border border-red-200',
  },
};

function getInitial(name: string | null): string {
  if (!name) return '?';
  return name.charAt(0).toUpperCase();
}

// `criado_em` é timestamp de evento (UTC no backend) — converte para hora local.
const formatTime = formatHora;
</script>

<template>
  <div
    class="bg-white rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm overflow-hidden"
  >
    <!-- Header -->
    <div class="p-4 md:p-6 border-b border-zinc-100 flex items-center gap-2">
      <ShoppingBag :size="18" class="text-zinc-500" />
      <h3 class="font-bold text-base md:text-lg text-zinc-900">Últimas Vendas</h3>
    </div>

    <!-- Error -->
    <div v-if="isError" class="p-8 text-center text-red-500 text-sm">
      Erro ao carregar vendas
    </div>

    <!-- Loading -->
    <div v-else-if="isLoading" class="p-6 space-y-3">
      <div v-for="i in 3" :key="i" class="h-12 bg-zinc-100 rounded-lg animate-pulse" />
    </div>

    <!-- Table -->
    <div v-else-if="vendas.length > 0" class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr
            class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100"
          >
            <th class="px-4 py-3">Cliente</th>
            <th class="px-4 py-3 text-right">Total</th>
            <th v-if="showTime" class="px-4 py-3 text-right">Hora</th>
            <th class="px-4 py-3 text-right">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr
            v-for="venda in vendas"
            :key="venda.id"
            class="hover:bg-zinc-50/50 transition-colors cursor-pointer"
            role="button"
            tabindex="0"
            @click="handleRowClick(venda)"
            @keydown.enter="handleRowClick(venda)"
          >
            <!-- Cliente -->
            <td class="px-4 py-2.5">
              <div class="flex items-center gap-2 text-xs md:text-sm font-semibold">
                <div
                  class="w-6 h-6 bg-brand-primary/10 text-brand-primary rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                >
                  {{ getInitial(venda.cliente_nome) }}
                </div>
                <span class="truncate max-w-24 md:max-w-32">{{
                  venda.cliente_nome ?? 'Consumidor'
                }}</span>
              </div>
            </td>

            <!-- Total -->
            <td class="px-4 py-2.5 text-xs md:text-sm font-bold text-zinc-900 text-right whitespace-nowrap">
              {{ formatCurrency(venda.total) }}
            </td>

            <!-- Hora -->
            <td v-if="showTime" class="px-4 py-2.5 text-xs text-zinc-400 text-right whitespace-nowrap">
              {{ formatTime(venda.criado_em) }}
            </td>

            <!-- Status -->
            <td class="px-4 py-2.5 text-right">
              <span
                :class="[
                  'px-2 py-0.5 rounded-full text-[10px] md:text-[11px] font-bold whitespace-nowrap',
                  statusConfig[venda.status]?.class ?? 'bg-zinc-100 text-zinc-500',
                ]"
              >
                {{ statusConfig[venda.status]?.label ?? venda.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div
      v-else
      class="p-8 text-center text-zinc-400 text-sm"
    >
      Nenhuma venda encontrada
    </div>
  </div>
</template>
