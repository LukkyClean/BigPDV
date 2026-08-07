<script setup lang="ts">
import { ref } from 'vue';
import { PackageCheck } from 'lucide-vue-next';
import { useOSCreateFlow } from '@/modules/order-service/ordens/composables/useOSCreateFlow';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
import { getUniqueOS } from '@/modules/order-service/ordens/services/orderServiceGet.service';
import { useToast } from '@/shared/composables/useToast';
import type { OSAguardandoRetiradaItemData } from '../../schemas/dashboard.schema';
import { formatData } from '@/shared/utils/date.utils';

interface Props {
  items: OSAguardandoRetiradaItemData[];
  isLoading: boolean;
  isError: boolean;
}

defineProps<Props>();

const { openExistingOS } = useOSCreateFlow();
// Rótulo do objeto por segmento: a oficina lê "Veículo" no cabeçalho, não "Equipamento".
const { labelSingular } = useObjetoLabels();
const toast = useToast();
const loadingOS = ref<string | null>(null);

async function handleRowClick(item: OSAguardandoRetiradaItemData) {
  if (loadingOS.value) return;
  loadingOS.value = item.numero_os;
  try {
    const os = await getUniqueOS(item.numero_os);
    openExistingOS(os);
  } catch {
    toast.error('Erro ao carregar OS');
  } finally {
    loadingOS.value = null;
  }
}

// `data_finalizacao` é timestamp de evento (UTC no backend).
function formatDate(dateStr: string | null): string {
  return formatData(dateStr, '—');
}
</script>

<template>
  <div class="bg-white rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm overflow-hidden flex flex-col">
    <div class="p-4 md:p-6 border-b border-zinc-100 flex items-center gap-2">
      <PackageCheck :size="18" class="text-zinc-500" />
      <h3 class="font-bold text-base md:text-lg text-zinc-900">Aguardando Retirada</h3>
      <span v-if="items.length > 0" class="ml-auto text-xs font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200 px-2 py-0.5 rounded-full">
        {{ items.length }}
      </span>
    </div>

    <div v-if="isError" class="p-8 text-center text-red-500 text-sm flex-1 flex items-center justify-center">
      Erro ao carregar
    </div>

    <div v-else-if="isLoading" class="p-6 space-y-3 flex-1">
      <div v-for="i in 3" :key="i" class="h-12 bg-zinc-100 rounded-lg animate-pulse" />
    </div>

    <div v-else-if="items.length > 0" class="overflow-x-auto flex-1">
      <table class="w-full text-left">
        <thead>
          <tr class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100">
            <th class="px-4 py-3">N° OS</th>
            <th class="px-4 py-3">Cliente</th>
            <th class="px-4 py-3">{{ labelSingular }}</th>
            <th class="px-4 py-3">Finalizada</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr
            v-for="item in items"
            :key="item.numero_os"
            :class="[
              'transition-colors cursor-pointer hover:bg-zinc-50/60',
              loadingOS === item.numero_os ? 'opacity-60 pointer-events-none' : '',
            ]"
            role="button"
            tabindex="0"
            @click="handleRowClick(item)"
            @keydown.enter="handleRowClick(item)"
          >
            <td class="px-4 py-3 text-xs font-semibold text-zinc-700">{{ item.numero_os }}</td>
            <td class="px-4 py-3 text-xs text-zinc-600 truncate max-w-28">{{ item.cliente_nome }}</td>
            <td class="px-4 py-3 text-xs text-zinc-500 truncate max-w-32">{{ item.equipamento }}</td>
            <td class="px-4 py-3 text-xs text-zinc-500 whitespace-nowrap">{{ formatDate(item.data_finalizacao) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="p-8 text-center text-zinc-400 text-sm flex-1 flex items-center justify-center">
      Nenhum {{ labelSingular.toLowerCase() }} aguardando retirada
    </div>
  </div>
</template>
