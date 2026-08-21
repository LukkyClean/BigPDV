<script setup lang="ts">
import { computed, ref, toRef } from 'vue';
import { Trophy, FileText } from 'lucide-vue-next';
import type { ChartConfiguration } from 'chart.js/auto';

import { formatCurrency } from '@/shared/utils/finance';
import { useCoresTema } from '@/shared/theme/useCoresTema';
import { useRankingQuery } from '../composables/useRankingQuery';
import ChartCanvas from './ChartCanvas.vue';
import ExtratoFuncionarioModal from './ExtratoFuncionarioModal.vue';

// Série única, cor institucional: segue o tema. Ler daqui (e não escrever o hex)
// é o que amarra o `config` à versão da paleta — quando a cor muda, o computed
// reavalia e o ChartCanvas repinta, inclusive durante a prévia ao vivo.
const { primaria } = useCoresTema();

const props = defineProps<{ inicio: string; fim: string }>();

const { data } = useRankingQuery(toRef(props, 'inicio'), toRef(props, 'fim'));
const itens = computed(() => data.value?.itens ?? []);

/**
 * O extrato de cada pessoa sai daqui.
 *
 * O ranking já tem `funcionario_id` e `nome` — abrir o extrato de uma linha não
 * custa consulta nenhuma a mais, e é onde o dono já está olhando quando a
 * pergunta "o que essa pessoa fez?" aparece.
 *
 * O id fica em `ref` e é o que habilita a query lá dentro: com `null` ela não
 * dispara, então o modal montado e fechado não busca nada.
 */
const extratoDe = ref<number | null>(null);

// Desenha o valor exato na ponta de cada barra (sempre visível, sem depender do hover).
const valueLabelPlugin = {
  id: 'valueLabel',
  afterDatasetsDraw(chart: any) {
    const { ctx } = chart;
    const meta = chart.getDatasetMeta(0);
    ctx.save();
    ctx.font = '600 11px system-ui, sans-serif';
    ctx.fillStyle = '#334155';
    ctx.textBaseline = 'middle';
    meta.data.forEach((bar: any, i: number) => {
      const val = Number(chart.data.datasets[0].data[i] ?? 0);
      ctx.fillText(formatCurrency(val), bar.x + 8, bar.y);
    });
    ctx.restore();
  },
};

const config = computed<ChartConfiguration>(() => ({
  type: 'bar',
  data: {
    labels: itens.value.map((i) => i.nome),
    datasets: [
      {
        label: 'Faturamento',
        data: itens.value.map((i) => i.faturamento_total),
        backgroundColor: primaria.value,
        borderRadius: 6,
        maxBarThickness: 34,
      },
    ],
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    // Espaço à direita pro rótulo de valor não ser cortado.
    layout: { padding: { right: 88 } },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => formatCurrency(Number(ctx.parsed.x ?? 0)) } },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { callback: (v) => formatCurrency(Number(v)) },
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
      },
      y: { grid: { display: false } },
    },
  },
  plugins: [valueLabelPlugin],
}));
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <h3 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2">
      <Trophy :size="15" class="text-brand-primary" /> Ranking por funcionário
    </h3>

    <div v-if="itens.length" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="h-64">
        <ChartCanvas :config="config" />
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-100">
          <thead>
            <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
              <th class="py-2 pr-3 font-semibold text-left">#</th>
              <th class="py-2 pr-3 font-semibold text-left">Funcionário</th>
              <th class="py-2 px-3 font-semibold text-right">Vendas</th>
              <th class="py-2 px-3 font-semibold text-right">OS</th>
              <th class="py-2 px-3 font-semibold text-right">Total</th>
              <th class="py-2 pl-3 font-semibold text-right"><span class="sr-only">Extrato</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(i, idx) in itens"
              :key="i.funcionario_id"
              class="border-b border-slate-100 last:border-0"
            >
              <td class="py-2 pr-3 text-slate-400 tabular-nums">{{ idx + 1 }}</td>
              <td class="py-2 pr-3 text-slate-700 font-medium">{{ i.nome }}</td>
              <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(i.faturamento_vendas) }}</td>
              <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(i.faturamento_os) }}</td>
              <td class="py-2 px-3 text-right font-semibold text-slate-800 tabular-nums">{{ formatCurrency(i.faturamento_total) }}</td>
              <td class="py-2 pl-3 text-right">
                <!-- Discreto de propósito: ícone sem rótulo, na cor de apoio,
                     como as ações rápidas da tabela de vendas. A coluna existe
                     para quem procura, não para disputar atenção com os números. -->
                <button
                  type="button"
                  class="p-1.5 rounded-lg text-slate-400 hover:text-brand-primary hover:bg-slate-100 transition-colors cursor-pointer"
                  :title="`Ver serviços de ${i.nome}`"
                  @click="extratoDe = i.funcionario_id"
                >
                  <FileText :size="15" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="py-8 text-center text-xs text-slate-400">
      Nenhum faturamento por funcionário no período.
    </div>

    <ExtratoFuncionarioModal
      :is-open="extratoDe !== null"
      :funcionario-id="extratoDe"
      :inicio="props.inicio"
      :fim="props.fim"
      @close="extratoDe = null"
    />
  </div>
</template>
