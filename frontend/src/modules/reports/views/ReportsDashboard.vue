<script setup lang="ts">
import { ref } from 'vue';
import { Banknote, Receipt, ShoppingCart, Wrench, TriangleAlert, Download } from 'lucide-vue-next';

import { formatCurrency, formatCentsToInput } from '@/shared/utils/finance';
import { saveCsv } from '@/shared/utils/csv';
import { useToast } from '@/shared/composables/useToast';
import { useFaturamentoQuery } from '../composables/useFaturamentoQuery';
import PeriodFilter from '../components/PeriodFilter.vue';
import KpiCard from '../components/KpiCard.vue';
import FaturamentoChart from '../components/FaturamentoChart.vue';
import FormasPagamentoDonut from '../components/FormasPagamentoDonut.vue';
import FaturamentoTabela from '../components/FaturamentoTabela.vue';
import RankingSection from '../components/RankingSection.vue';

const inicio = ref('');
const fim = ref('');
function onPeriodo(r: { inicio: string; fim: string }) {
  inicio.value = r.inicio;
  fim.value = r.fim;
}

const { data, isLoading, isError } = useFaturamentoQuery(inicio, fim);
const toast = useToast();

/** Exporta o detalhamento por dia (dias com movimento) como CSV e abre no Excel. */
async function exportarCsv() {
  const d = data.value;
  if (!d) return;
  const linhas = d.por_dia
    .filter((x) => x.total_geral > 0)
    .map((x) => [
      x.dia,
      formatCentsToInput(x.total_vendas),
      formatCentsToInput(x.total_os),
      formatCentsToInput(x.total_geral),
    ]);
  const caminho = await saveCsv(
    `faturamento_${d.inicio}_a_${d.fim}.csv`,
    ['Dia', 'Vendas (R$)', 'OS (R$)', 'Total (R$)'],
    linhas,
  );
  if (caminho) toast.success(`Planilha salva em: ${caminho}`);
}
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <PeriodFilter @change="onPeriodo" />
      <button
        type="button"
        :disabled="!data"
        class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:border-brand-primary hover:text-brand-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        @click="exportarCsv"
      >
        <Download :size="14" /> Exportar CSV
      </button>
    </div>

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

      <!-- Ranking por funcionário -->
      <RankingSection :inicio="inicio" :fim="fim" />

      <!-- Tabela -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-bold text-slate-700 mb-3">Detalhamento por dia</h3>
        <FaturamentoTabela v-if="data" :por-dia="data.por_dia" />
      </div>

      <p v-if="isLoading" class="text-center text-slate-400 text-xs py-2">Atualizando…</p>
    </template>
  </div>
</template>
