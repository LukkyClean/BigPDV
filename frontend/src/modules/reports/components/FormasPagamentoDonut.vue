<script setup lang="ts">
import { computed } from 'vue';
import type { ChartConfiguration } from 'chart.js/auto';
import ChartCanvas from './ChartCanvas.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { FormaPagamentoResumo } from '../schemas/faturamento.schema';

const props = defineProps<{ formas: FormaPagamentoResumo[] }>();

const PALETTE = ['#045ca1', '#5590bf', '#0891b2', '#16a34a', '#d97706', '#9333ea', '#dc2626', '#64748b'];

const config = computed<ChartConfiguration>(() => ({
  type: 'doughnut',
  data: {
    labels: props.formas.map((f) => f.nome),
    datasets: [
      {
        data: props.formas.map((f) => f.valor_total),
        backgroundColor: props.formas.map((_, i) => PALETTE[i % PALETTE.length]),
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
