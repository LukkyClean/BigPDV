<script setup lang="ts">
import { ref, computed } from 'vue';
import { Banknote, Receipt, ShoppingCart, Wrench, TriangleAlert, Download, Percent } from 'lucide-vue-next';

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
import ComissaoSection from '../components/ComissaoSection.vue';
import EstoqueSection from '../components/EstoqueSection.vue';
import OSPerformanceSection from '../components/OSPerformanceSection.vue';

const inicio = ref('');
const fim = ref('');
function onPeriodo(r: { inicio: string; fim: string }) {
  inicio.value = r.inicio;
  fim.value = r.fim;
}

const { data, isLoading, isError } = useFaturamentoQuery(inicio, fim);
const toast = useToast();

/** Só mostra o bloco de juros quando houve juros — repassado ou absorvido. */
const jurosTotal = computed(
  () => (data.value?.juros_repassado ?? 0) + (data.value?.juros_absorvido ?? 0),
);

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
        <!--
          Mostra o LÍQUIDO: é o que efetivamente entrou no caixa. O juros de
          cartão vai para a operadora, então exibi-lo aqui dizia que um dinheiro
          que nunca chegou na loja tinha chegado. O bruto continua visível, na
          linha de apoio e no desdobramento abaixo.
        -->
        <KpiCard
          label="Faturamento"
          :value="formatCurrency(data?.faturamento_liquido ?? data?.faturamento_total ?? 0)"
          :icon="Banknote"
          :hint="jurosTotal > 0
            ? `Bruto ${formatCurrency(data?.faturamento_total ?? 0)} − ${formatCurrency(jurosTotal)} de juros`
            : `${data?.qtd_vendas ?? 0} vendas · ${data?.qtd_os ?? 0} OS`"
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

      <!--
        Juros de cartão. Só aparece quando existe — loja que não cobra juros não
        precisa ver a linha. O repassado já está dentro do faturamento bruto; o
        absorvido nunca entrou nele. Os dois vão para a operadora, então os dois
        saem do líquido.
      -->
      <div
        v-if="jurosTotal > 0"
        class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm"
      >
        <h3 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-1.5">
          <Percent :size="14" class="text-slate-400" /> Juros de cartão no período
        </h3>
        <p class="text-xs text-slate-500 mb-3">
          Juros de cartão fica com a operadora, não com a loja — por isso sai do faturamento.
        </p>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between items-center">
            <span class="text-slate-500">Faturamento bruto</span>
            <span class="font-medium text-slate-700 tabular-nums">
              {{ formatCurrency(data?.faturamento_total ?? 0) }}
            </span>
          </div>
          <div v-if="(data?.juros_repassado ?? 0) > 0" class="flex justify-between items-center">
            <span class="text-amber-600">
              (−) Juros repassado ao cliente
              <span class="text-[11px] text-slate-400">· cobrado a mais, fica com a operadora</span>
            </span>
            <span class="font-medium text-amber-600 tabular-nums">
              − {{ formatCurrency(data?.juros_repassado ?? 0) }}
            </span>
          </div>
          <div v-if="(data?.juros_absorvido ?? 0) > 0" class="flex justify-between items-center">
            <span class="text-rose-600">
              (−) Juros absorvido pela loja
              <span class="text-[11px] text-slate-400">· o cliente não pagou, a loja bancou</span>
            </span>
            <span class="font-medium text-rose-600 tabular-nums">
              − {{ formatCurrency(data?.juros_absorvido ?? 0) }}
            </span>
          </div>
          <div class="flex justify-between items-center border-t border-slate-200 pt-2">
            <span class="font-bold text-slate-700">Faturamento líquido</span>
            <span class="text-lg font-bold text-emerald-700 tabular-nums">
              {{ formatCurrency(data?.faturamento_liquido ?? data?.faturamento_total ?? 0) }}
            </span>
          </div>
        </div>
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

      <!-- Comissão por funcionário -->
      <ComissaoSection :inicio="inicio" :fim="fim" />

      <!-- Estoque e Curva ABC -->
      <EstoqueSection :inicio="inicio" :fim="fim" />

      <!-- Desempenho de OS -->
      <OSPerformanceSection :inicio="inicio" :fim="fim" />

      <!-- Tabela -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-bold text-slate-700 mb-3">Detalhamento por dia</h3>
        <FaturamentoTabela v-if="data" :por-dia="data.por_dia" />
      </div>

      <p v-if="isLoading" class="text-center text-slate-400 text-xs py-2">Atualizando…</p>
    </template>
  </div>
</template>
