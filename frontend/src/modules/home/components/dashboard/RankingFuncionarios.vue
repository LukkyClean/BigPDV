<script setup lang="ts">
import { Trophy } from 'lucide-vue-next';
import { formatCurrency } from '@/shared/utils/finance';
import type { RankingFuncionarioItemData } from '../../schemas/dashboard.schema';

interface Props {
  items: RankingFuncionarioItemData[];
  isLoading: boolean;
  isError: boolean;
}

defineProps<Props>();

const medalha: Record<number, string> = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
};
</script>

<template>
  <div class="bg-white rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm overflow-hidden flex flex-col">
    <div class="p-4 md:p-6 border-b border-zinc-100 flex items-center gap-2">
      <Trophy :size="18" class="text-zinc-500" />
      <h3 class="font-bold text-base md:text-lg text-zinc-900">Ranking de Funcionários</h3>
    </div>

    <div v-if="isError" class="p-8 text-center text-red-500 text-sm flex-1 flex items-center justify-center">
      Erro ao carregar ranking
    </div>

    <div v-else-if="isLoading" class="p-6 space-y-3 flex-1">
      <div v-for="i in 5" :key="i" class="h-12 bg-zinc-100 rounded-lg animate-pulse" />
    </div>

    <div v-else-if="items.length > 0" class="overflow-x-auto flex-1">
      <table class="w-full text-left min-w-80">
        <thead>
          <tr class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100">
            <th class="px-4 md:px-5 py-3">#</th>
            <th class="px-4 md:px-5 py-3">Funcionário</th>
            <th class="px-4 md:px-5 py-3 text-right">Vendas</th>
            <th class="px-4 md:px-5 py-3 text-right">Serviços</th>
            <th class="px-4 md:px-5 py-3 text-right">OS Fechadas</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr v-for="item in items" :key="item.id" class="hover:bg-zinc-50/60 transition-colors">
            <td class="px-4 md:px-5 py-3 text-sm font-bold text-zinc-700 w-10">
              {{ medalha[item.posicao] ?? item.posicao }}
            </td>
            <td class="px-4 md:px-5 py-3 text-sm font-medium text-zinc-800">
              {{ item.nome }}
            </td>
            <td class="px-4 md:px-5 py-3 text-sm font-semibold text-zinc-700 text-right whitespace-nowrap">
              {{ formatCurrency(item.total_vendas_valor) }}
            </td>
            <td class="px-4 md:px-5 py-3 text-sm font-semibold text-zinc-700 text-right whitespace-nowrap">
              {{ formatCurrency(item.total_os_valor) }}
            </td>
            <td class="px-4 md:px-5 py-3 text-sm text-zinc-500 text-right">
              {{ item.qtd_os_fechadas }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="p-8 text-center text-zinc-400 text-sm flex-1 flex items-center justify-center">
      Nenhum dado no período
    </div>
  </div>
</template>
