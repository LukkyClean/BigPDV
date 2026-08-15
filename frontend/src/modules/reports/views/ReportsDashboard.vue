<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import { Banknote, Receipt, ShoppingCart, Wrench, TriangleAlert, Percent, Wallet, AlertTriangle, Printer } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { imprimirComPagina } from '@/shared/utils/print.utils';
import FinanceiroPrint from '../components/FinanceiroPrint.vue';
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
import CaixaSection from '../components/CaixaSection.vue';
import { useOrdemServico } from '@/shared/composables/useOrdemServico';
import { useSessaoCaixaQuery } from '@/modules/sales/caixa/composables/queries/useSessaoCaixaQuery';

const inicio = ref('');
const fim = ref('');
function onPeriodo(r: { inicio: string; fim: string }) {
  inicio.value = r.inicio;
  fim.value = r.fim;
}

const { data, isLoading, isError } = useFaturamentoQuery(inicio, fim);
const { usaOrdemServico } = useOrdemServico();
const { caixaHabilitado } = useSessaoCaixaQuery();

/** Só mostra o bloco de juros quando houve juros — repassado ou absorvido. */
const jurosTotal = computed(
  () => (data.value?.juros_repassado ?? 0) + (data.value?.juros_absorvido ?? 0),
);

/**
 * O bloco de lucro só aparece quando há custo apurado OU um aviso a dar. Loja
 * que só vende serviço não tem CMV, e um "Lucro = Faturamento" fixo na tela não
 * informaria nada — só ocuparia espaço sugerindo margem de 100%.
 */
const temCusto = computed(
  () => (data.value?.cmv ?? 0) > 0 || (data.value?.saidas_sem_custo ?? 0) > 0,
);

const lucroPositivo = computed(() => (data.value?.lucro_bruto ?? 0) >= 0);

/**
 * Impressão A4 — mesmo sistema da folha de comissão e das impressões de OS.
 * Imprime o período que está no filtro, não um mês fixo: o botão entrega o que
 * está na tela, senão o papel e o monitor discordariam.
 */
const mostrarImpressao = ref(false);
async function imprimirFinanceiro() {
  if (!data.value) return;
  mostrarImpressao.value = true;
  await nextTick();
  let fallback: ReturnType<typeof setTimeout>;
  const limpar = () => {
    mostrarImpressao.value = false;
    window.removeEventListener('afterprint', limpar);
    clearTimeout(fallback);
  };
  window.addEventListener('afterprint', limpar);
  fallback = setTimeout(limpar, 60000);
  imprimirComPagina('A4');
}

</script>

<template>
  <div class="p-6 max-w-7xl mx-auto space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <PeriodFilter @change="onPeriodo" />
      <button
        type="button"
        :disabled="!data"
        class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-brand-primary text-white text-xs font-semibold hover:bg-brand-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        @click="imprimirFinanceiro"
      >
        <Printer :size="14" /> Imprimir relatório
      </button>
    </div>

    <!-- Relatório imprimível (A4) — só renderiza durante a impressão -->
    <FinanceiroPrint v-if="mostrarImpressao && data" :dados="data" />

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
            : usaOrdemServico
              ? `${data?.qtd_vendas ?? 0} vendas · ${data?.qtd_os ?? 0} OS`
              : `${data?.qtd_vendas ?? 0} vendas`"
        />
        <KpiCard label="Ticket médio" :value="formatCurrency(data?.ticket_medio ?? 0)" :icon="Receipt" />
        <KpiCard
          label="Vendas"
          :value="formatCurrency(data?.faturamento_vendas ?? 0)"
          :icon="ShoppingCart"
          :hint="`${data?.qtd_vendas ?? 0} finalizadas`"
        />
        <!-- Loja sem Ordem de Serviço não tem faturamento de serviço para mostrar. -->
        <KpiCard
          v-if="usaOrdemServico"
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

      <!--
        Lucro. É a resposta para "vendi por 150, a peça me custou 40, quanto
        sobrou?". O custo vem congelado do livro de estoque, do dia em que a peça
        saiu — não do preço de hoje no cadastro, senão um reajuste do fornecedor
        reescreveria o lucro do mês passado.
      -->
      <div v-if="temCusto" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-1.5">
          <Wallet :size="14" class="text-slate-400" /> Lucro no período
        </h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between items-center">
            <span class="text-slate-500">Faturamento líquido</span>
            <span class="font-medium text-slate-700 tabular-nums">
              {{ formatCurrency(data?.faturamento_liquido ?? data?.faturamento_total ?? 0) }}
            </span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-rose-600">
              (−) Custo das peças vendidas
              <span class="text-[11px] text-slate-400">· o que você pagou por elas</span>
            </span>
            <span class="font-medium text-rose-600 tabular-nums">
              − {{ formatCurrency(data?.cmv ?? 0) }}
            </span>
          </div>
          <div class="flex justify-between items-center border-t border-slate-200 pt-2">
            <span class="font-bold text-slate-700">
              Lucro bruto
              <span class="text-[11px] font-normal text-slate-400">· não desconta despesa fixa</span>
            </span>
            <span class="text-lg font-bold tabular-nums" :class="lucroPositivo ? 'text-emerald-700' : 'text-rose-700'">
              {{ formatCurrency(data?.lucro_bruto ?? 0) }}
              <span class="text-xs font-semibold text-slate-400">
                ({{ (data?.margem_percentual ?? 0).toFixed(1) }}%)
              </span>
            </span>
          </div>
        </div>

        <!--
          Honestidade sobre o dado: movimentação anterior ao registro de custo
          entra como zero no CMV, então o lucro fica MAIOR do que foi. Melhor
          avisar do que exibir um número bonito e errado.
        -->
        <p
          v-if="(data?.saidas_sem_custo ?? 0) > 0"
          class="mt-3 flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2.5"
        >
          <AlertTriangle :size="14" class="shrink-0 mt-px" />
          <span>
            {{ data?.saidas_sem_custo }} movimentação(ões) deste período são anteriores ao
            registro de custo e entraram como zero. <strong>O lucro acima está maior do que o
            real</strong> — ele fica exato conforme as peças forem entrando com o valor pago.
          </span>
        </p>
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

      <!-- Caixa: quem abriu, quem fechou e com qual diferenca. So aparece
           para quem usa controle de caixa. -->
      <CaixaSection v-if="caixaHabilitado" :inicio="inicio" :fim="fim" />

      <!-- Estoque e Curva ABC -->
      <EstoqueSection :inicio="inicio" :fim="fim" />

      <!-- Desempenho de OS. O v-if desmonta o componente, e com ele a
           useOSPerformanceQuery: numa loja de PDV a requisição nem sai. -->
      <OSPerformanceSection v-if="usaOrdemServico" :inicio="inicio" :fim="fim" />

      <!-- Tabela -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 class="text-sm font-bold text-slate-700 mb-3">Detalhamento por dia</h3>
        <FaturamentoTabela v-if="data" :por-dia="data.por_dia" />
      </div>

      <p v-if="isLoading" class="text-center text-slate-400 text-xs py-2">Atualizando…</p>
    </template>
  </div>
</template>
