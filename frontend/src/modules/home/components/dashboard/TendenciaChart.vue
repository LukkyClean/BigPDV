<script setup lang="ts">
/**
 * @component TendenciaChart
 * @description Gráfico de linha do faturamento por dia (vendas + OS) no período.
 *   Autocontido no módulo home (Chart.js/auto direto) para não depender de outro módulo.
 *   Valores em centavos; formatCurrency (que espera centavos) formata eixo e tooltip.
 */
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue';
import { Chart, type ChartConfiguration } from 'chart.js/auto';

import { formatCurrency } from '@/shared/utils/finance';
import type { TendenciaDiaItemData } from '../../schemas/dashboard.schema';

const props = defineProps<{ porDia: TendenciaDiaItemData[] }>();

function labelDia(iso: string): string {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

const config = computed<ChartConfiguration>(() => ({
  type: 'line',
  data: {
    labels: props.porDia.map((d) => labelDia(d.dia)),
    datasets: [
      {
        label: 'Faturamento',
        data: props.porDia.map((d) => d.total_geral),
        borderColor: '#045ca1',
        backgroundColor: 'rgba(4, 92, 161, 0.08)',
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: props.porDia.length > 31 ? 0 : 3,
        pointBackgroundColor: '#045ca1',
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

const canvas = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

function render() {
  if (!canvas.value) return;
  chart?.destroy();
  chart = new Chart(canvas.value, config.value);
}

onMounted(render);
watch(config, render, { deep: true });
onBeforeUnmount(() => {
  chart?.destroy();
  chart = null;
});
</script>

<template>
  <div class="relative w-full h-full">
    <canvas ref="canvas" />
  </div>
</template>
