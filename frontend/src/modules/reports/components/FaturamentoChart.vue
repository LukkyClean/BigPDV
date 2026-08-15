<script setup lang="ts">
import { computed } from 'vue';
import type { ChartConfiguration } from 'chart.js/auto';
import ChartCanvas from './ChartCanvas.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { useCoresTema, comAlpha } from '@/shared/theme/useCoresTema';
import type { FaturamentoDia } from '../schemas/faturamento.schema';

const props = defineProps<{ porDia: FaturamentoDia[] }>();

// Série única, cor institucional: segue o tema. O azul estava chumbado em três
// pontos aqui — escapou da varredura por ser valor literal em JS, não classe.
const { primaria } = useCoresTema();

function labelDia(iso: string): string {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

// Dados em centavos; formatCurrency (que espera centavos) formata eixo e tooltip.
const config = computed<ChartConfiguration>(() => ({
  type: 'line',
  data: {
    labels: props.porDia.map((d) => labelDia(d.dia)),
    datasets: [
      {
        label: 'Faturamento',
        data: props.porDia.map((d) => d.total_geral),
        borderColor: primaria.value,
        backgroundColor: comAlpha(primaria.value, 0.08),
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: props.porDia.length > 31 ? 0 : 3,
        pointBackgroundColor: primaria.value,
        pointHoverRadius: 5,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: { label: (ctx) => formatCurrency(Number(ctx.parsed.y ?? 0)) },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { callback: (v) => formatCurrency(Number(v)) },
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
      },
      x: { grid: { display: false } },
    },
  },
}));
</script>

<template>
  <ChartCanvas :config="config" />
</template>
