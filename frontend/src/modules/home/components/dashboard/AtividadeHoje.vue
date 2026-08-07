<script setup lang="ts">
import { Activity, ShoppingCart, Wrench } from 'lucide-vue-next';
import { formatCurrency } from '@/shared/utils/finance';
import { useSaleModal } from '@/modules/sales/composables/flows/useSaleModal';
import { useOSCreateFlow } from '@/modules/order-service/ordens/composables/useOSCreateFlow';
import { getUniqueOS } from '@/modules/order-service/ordens/services/orderServiceGet.service';
import { useToast } from '@/shared/composables/useToast';
import { ref } from 'vue';
import type { AtividadeItemData } from '../../schemas/dashboard.schema';
import { formatHora } from '@/shared/utils/date.utils';

interface Props {
  items: AtividadeItemData[];
  isLoading: boolean;
  isError: boolean;
}

defineProps<Props>();

const { openSaleEditModal, openSaleViewModal } = useSaleModal();
const { openExistingOS } = useOSCreateFlow();
const toast = useToast();
const loadingRef = ref<string | null>(null);

async function handleClick(item: AtividadeItemData) {
  if (loadingRef.value) return;
  loadingRef.value = item.referencia;

  try {
    if (item.tipo === 'venda') {
      const id = parseInt(item.referencia.replace('#', ''));
      if (item.status === 'ATIVA') {
        openSaleEditModal(id);
      } else {
        openSaleViewModal(id);
      }
    } else {
      const os = await getUniqueOS(item.referencia);
      openExistingOS(os);
    }
  } catch {
    toast.error('Erro ao abrir registro');
  } finally {
    loadingRef.value = null;
  }
}

// `horario` é timestamp de evento (UTC no backend) — converte para hora local.
const formatTime = formatHora;

const statusConfig: Record<string, { label: string; class: string }> = {
  ATIVA:        { label: 'Ativa',        class: 'bg-blue-50 text-blue-600 border border-blue-200' },
  FINALIZADA:   { label: 'Finalizada',   class: 'bg-emerald-50 text-emerald-600 border border-emerald-200' },
  CANCELADA:    { label: 'Cancelada',    class: 'bg-red-50 text-red-600 border border-red-200' },
  ABERTA:       { label: 'Aberta',       class: 'bg-zinc-100 text-zinc-600 border border-zinc-200' },
  EM_ANDAMENTO: { label: 'Andamento',    class: 'bg-amber-50 text-amber-600 border border-amber-200' },
  AGUARDANDO_PECAS:     { label: 'Aguard. peças', class: 'bg-orange-50 text-orange-600 border border-orange-200' },
  AGUARDANDO_APROVACAO: { label: 'Aguard. aprova.', class: 'bg-violet-50 text-violet-600 border border-violet-200' },
  AGUARDANDO_RETIRADA:  { label: 'P/ Retirada', class: 'bg-teal-50 text-teal-600 border border-teal-200' },
};
</script>

<template>
  <div class="bg-white rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm overflow-hidden flex flex-col">
    <div class="p-4 md:p-6 border-b border-zinc-100 flex items-center gap-2">
      <Activity :size="18" class="text-zinc-500" />
      <h3 class="font-bold text-base md:text-lg text-zinc-900">Atividade de Hoje</h3>
    </div>

    <div v-if="isError" class="p-8 text-center text-red-500 text-sm flex-1 flex items-center justify-center">
      Erro ao carregar atividades
    </div>

    <div v-else-if="isLoading" class="p-6 space-y-3 flex-1">
      <div v-for="i in 5" :key="i" class="h-10 bg-zinc-100 rounded-lg animate-pulse" />
    </div>

    <div v-else-if="items.length > 0" class="flex-1 overflow-y-auto max-h-80">
      <ul class="divide-y divide-zinc-100">
        <li
          v-for="item in items"
          :key="`${item.tipo}-${item.referencia}-${item.horario}`"
          :class="[
            'flex items-center gap-3 px-4 md:px-5 py-3 cursor-pointer hover:bg-zinc-50/60 transition-colors',
            loadingRef === item.referencia ? 'opacity-60 pointer-events-none' : '',
          ]"
          role="button"
          tabindex="0"
          @click="handleClick(item)"
          @keydown.enter="handleClick(item)"
        >
          <!-- Hora -->
          <span class="text-[11px] font-mono text-zinc-400 shrink-0 w-10">
            {{ formatTime(item.horario) }}
          </span>

          <!-- Ícone tipo -->
          <div :class="['w-7 h-7 rounded-lg flex items-center justify-center shrink-0', item.tipo === 'venda' ? 'bg-blue-50' : 'bg-zinc-100']">
            <ShoppingCart v-if="item.tipo === 'venda'" :size="13" class="text-blue-500" />
            <Wrench v-else :size="13" class="text-zinc-500" />
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-zinc-800 truncate">
              {{ item.referencia }} · {{ item.cliente_nome ?? 'Consumidor' }}
            </p>
            <p v-if="item.valor > 0" class="text-[11px] text-zinc-400">
              {{ formatCurrency(item.valor) }}
            </p>
          </div>

          <!-- Status -->
          <span :class="['px-1.5 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap shrink-0', statusConfig[item.status]?.class ?? 'bg-zinc-100 text-zinc-500']">
            {{ statusConfig[item.status]?.label ?? item.status }}
          </span>
        </li>
      </ul>
    </div>

    <div v-else class="p-8 text-center flex-1 flex flex-col items-center justify-center gap-2">
      <Activity :size="28" class="text-zinc-200" />
      <p class="text-zinc-400 text-sm">Nenhuma atividade hoje ainda</p>
      <p class="text-zinc-300 text-xs">Suas vendas e OS criadas hoje aparecerão aqui</p>
    </div>
  </div>
</template>
