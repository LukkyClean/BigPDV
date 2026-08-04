<script setup lang="ts">
import { computed } from 'vue';
import type { ChartConfiguration } from 'chart.js/auto';
import ChartCanvas from './ChartCanvas.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { useCoresTema } from '@/shared/theme/useCoresTema';
import type { FormaPagamentoResumo } from '../schemas/faturamento.schema';

const props = defineProps<{ formas: FormaPagamentoResumo[] }>();

const { primaria, secundaria } = useCoresTema();

/**
 * Paleta CATEGÓRICA: a função dela é fazer as fatias serem distinguíveis ENTRE
 * SI, não expressar a marca. Derivar todas de uma cor só daria oito tons
 * parecidos e o gráfico perderia justamente o que ele faz.
 *
 * Só as duas primeiras seguem o tema — a fatia dominante puxa para a marca e o
 * resto mantém a leitura do conjunto. Mesmo critério dos azuis semânticos que
 * ficaram: cor que carrega informação não segue tema.
 */
const CORES_FIXAS = ['#0891b2', '#16a34a', '#d97706', '#9333ea', '#dc2626', '#64748b'];

const paleta = computed(() => [primaria.value, secundaria.value, ...CORES_FIXAS]);

const config = computed<ChartConfiguration>(() => ({
  type: 'doughnut',
  data: {
    labels: props.formas.map((f) => f.nome),
    datasets: [
      {
        data: props.formas.map((f) => f.valor_total),
        backgroundColor: props.formas.map((_, i) => paleta.value[i % paleta.value.length]),
        borderWidth: 0,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
      tooltip: {
        callbacks: { label: (ctx) => `${ctx.label}: ${formatCurrency(Number(ctx.parsed))}` },
      },
    },
  },
}));
</script>

<template>
  <ChartCanvas :config="config" />
</template>
