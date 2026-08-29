<script setup lang="ts">
/**
 * Barras empilhadas: quanto entrou por mês, e de onde veio.
 *
 * Autocontido (Chart.js direto), no mesmo padrão do `TendenciaChart` do
 * dashboard — não vale criar dependência entre módulos por causa de um
 * gráfico.
 *
 * O componente NÃO conhece origem nenhuma: ele monta um conjunto por chave que
 * chegar, com o rótulo que chegar. Uma loja PDV desenha uma barra sólida; uma
 * oficina desenha duas cores. Segmento novo não passa por aqui.
 */
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue';
import { Chart, type ChartConfiguration } from 'chart.js/auto';

import { formatCurrency } from '@/shared/utils/finance';
import { useCoresTema, comAlpha } from '@/shared/theme/useCoresTema';

import type { SerieMes } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ meses: SerieMes[] }>();

const { primaria, secundaria } = useCoresTema();

/**
 * A cor de cada origem, na ordem em que ela aparece.
 *
 * As duas primeiras saem do tema da loja — que o `check-paleta` já garante
 * legível em qualquer cor que o dono escolha. As seguintes são neutras e fixas:
 * hoje só existem duas origens, e inventar mais cores derivadas sem alguém para
 * conferir contraste seria criar um problema para um caso que não existe.
 */
const RESERVAS = ['#64748b', '#0ea5e9', '#a855f7'];

function rotuloMes(mes: string): string {
  const [ano, m] = mes.split('-');
  const nomes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
                 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  return `${nomes[Number(m) - 1]}/${ano.slice(2)}`;
}

/** As origens presentes na janela, na ordem em que aparecem no primeiro mês. */
const origens = computed(() => {
  const vistas = new Map<string, string>();
  for (const mes of props.meses) {
    for (const origem of mes.origens) {
      if (!vistas.has(origem.chave)) vistas.set(origem.chave, origem.rotulo);
    }
  }
  return [...vistas.entries()].map(([chave, rotulo]) => ({ chave, rotulo }));
});

const config = computed<ChartConfiguration>(() => ({
  type: 'bar',
  data: {
    labels: props.meses.map((m) => rotuloMes(m.mes)),
    datasets: origens.value.map((origem, indice) => {
      const cor =
        indice === 0
          ? primaria.value
          : indice === 1
            ? secundaria.value
            : RESERVAS[(indice - 2) % RESERVAS.length];
      return {
        label: origem.rotulo,
        data: props.meses.map(
          (m) => m.origens.find((o) => o.chave === origem.chave)?.total ?? 0,
        ),
        backgroundColor: comAlpha(cor, 0.85),
        borderRadius: 4,
        stack: 'receita',
      };
    }),
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: origens.value.length > 1,
        position: 'bottom',
        labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true },
      },
      tooltip: {
        callbacks: {
          label: (item) => `${item.dataset.label}: ${formatCurrency(Number(item.raw))}`,
          footer: (itens) =>
            itens.length > 1
              ? `Total: ${formatCurrency(itens.reduce((s, i) => s + Number(i.raw), 0))}`
              : '',
        },
      },
    },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: {
        stacked: true,
        beginAtZero: true,
        ticks: { callback: (valor) => formatCurrency(Number(valor)) },
      },
    },
  },
}));

const canvas = ref<HTMLCanvasElement | null>(null);
let grafico: Chart | null = null;

onMounted(() => {
  if (canvas.value) grafico = new Chart(canvas.value, config.value);
});

// Repinta quando a série OU a paleta da loja mudam.
watch(config, (novo) => {
  if (!grafico) return;
  grafico.data = novo.data;
  grafico.options = novo.options ?? {};
  grafico.update();
});

onBeforeUnmount(() => {
  grafico?.destroy();
  grafico = null;
});
</script>

<template>
  <div class="h-72">
    <canvas ref="canvas" />
  </div>
</template>
