<script setup lang="ts">
import { ref } from 'vue';
import { Banknote, Receipt, ShoppingCart, Wrench, TriangleAlert } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { useFaturamentoQuery } from '../composables/useFaturamentoQuery';
import PeriodFilter from '../components/PeriodFilter.vue';
import KpiCard from '../components/KpiCard.vue';
import FaturamentoChart from '../components/FaturamentoChart.vue';
import FormasPagamentoDonut from '../components/FormasPagamentoDonut.vue';
import FaturamentoTabela from '../components/FaturamentoTabela.vue';

const inicio = ref('');
const fim = ref('');
function onPeriodo(r: { inicio: string; fim: string }) {
  inicio.value = r.inicio;
  fim.value = r.fim;
}

const { data, isLoading, isError } = useFaturamentoQuery(inicio, fim);
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto space-y-5">
    <PeriodFilter @change="onPeriodo" />

    <div
      v-if="isError"
      class="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600"
    >
      <TriangleAlert :size="16" />
      Não foi possível carregar o relatório. Tente novamente.
    </div>

    <template v-else>
      <!-- KPIs -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Faturamento"
          :value="formatCurrency(data?.faturamento_total ?? 0)"
          :icon="Banknote"
          :hint="`${data?.qtd_vendas ?? 0} vendas · ${data?.qtd_os ?? 0} OS`"
        />
        <KpiCard label="Ticket médio" :value="formatCurrency(data?.ticket_medio ?? 0)" :icon="Receipt" />
        <KpiCard
          label="Vendas"
          :value="formatCurrency(data?.faturamento_vendas ?? 0)"
          :icon="ShoppingCart"
          :hint="`${data?.qtd_vendas ?? 0} finalizadas`"
        />
        <KpiCard
          label="Serviços (OS)"
          :value="formatCurrency(data?.faturamento_os ?? 0)"
          :icon="Wrench"
          :hint="`${data?.qtd_os ?? 0} finalizadas`"
        />
      </div>

      <!-- Gráficos -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h3 class="text-sm font-bold text-slate-700 mb-3">Evolução do faturamento</h3>
          <div class="h-72">
            <FaturamentoChart v-if="data" :por-dia="data.por_dia" />
          </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h3 class="text-sm font-bold text-slate-700 mb-3">Formas de pagamento</h3>
          <div class="h-72">
            <FormasPagamentoDonut
              v-if="data && data.formas_pagamento.length"
              :formas="data.formas_pagamento"
            />
            <div v-else class="h-full grid place-items-center text-xs text-slate-400">
              Sem pagamentos no período.
            </div>
          </div>
        </div>
      </div>

      <!-- Tabela -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-bold text-slate-700 mb-3">Detalhamento por dia</h3>
        <FaturamentoTabela v-if="data" :por-dia="data.por_dia" />
      </div>

      <p v-if="isLoading" class="text-center text-slate-400 text-xs py-2">Atualizando…</p>
    </template>
  </div>
</template>
