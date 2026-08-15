<script setup lang="ts">
import { computed } from 'vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { FaturamentoDia } from '../schemas/faturamento.schema';

const props = defineProps<{ porDia: FaturamentoDia[] }>();

function fmtDia(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

// Só dias com movimento, mais recentes primeiro.
const linhas = computed(() => props.porDia.filter((d) => d.total_geral > 0).slice().reverse());
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm min-w-100">
      <thead>
        <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
          <th class="py-2 pr-3 font-semibold text-left">Dia</th>
          <th class="py-2 px-3 font-semibold text-right">Vendas</th>
          <th class="py-2 px-3 font-semibold text-right">OS</th>
          <th class="py-2 pl-3 font-semibold text-right">Total</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in linhas" :key="l.dia" class="border-b border-slate-100 last:border-0">
          <td class="py-2 pr-3 text-slate-600">{{ fmtDia(l.dia) }}</td>
          <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(l.total_vendas) }}</td>
          <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(l.total_os) }}</td>
          <td class="py-2 pl-3 text-right font-semibold text-slate-800 tabular-nums">{{ formatCurrency(l.total_geral) }}</td>
        </tr>
        <tr v-if="linhas.length === 0">
          <td colspan="4" class="py-6 text-center text-slate-400 text-xs">Nenhum faturamento no período.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
