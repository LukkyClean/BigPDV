<script setup lang="ts">
import { useOrdemServico } from '@/shared/composables/useOrdemServico';
import { ref, computed } from 'vue';
import { TrendingUp, ShoppingCart, Wrench, CheckCircle } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseStatsCard from '@/shared/components/layout/StatsCard/BaseStatsCard.vue';
import OSAtrasadasBanner from './OSAtrasadasBanner.vue';
import MinhaFilaTable from './MinhaFilaTable.vue';
import RecentTransactions from './RecentTransactions.vue';
import OSAguardandoRetiradaTable from './OSAguardandoRetiradaTable.vue';
import AtividadeHoje from './AtividadeHoje.vue';
import TendenciaChart from './TendenciaChart.vue';

import { useAuthStore } from '@/shared/stores/auth.store';
import { formatCurrency } from '@/shared/utils/finance';
import { useMeuResumoQuery } from '../../composables/queries/useMeuResumoQuery';
import { useMinhasUltimasVendasQuery } from '../../composables/queries/useMinhasUltimasVendasQuery';
import { useMinhaFilaQuery } from '../../composables/queries/useMinhaFilaQuery';
import { useMinhasOSAtrasadasQuery } from '../../composables/queries/useMinhasOSAtrasadasQuery';
import { useOSAguardandoRetiradaQuery } from '../../composables/queries/useOSAguardandoRetiradaQuery';
import { useMinhaAtividadeHojeQuery } from '../../composables/queries/useMinhaAtividadeHojeQuery';
import { useMinhaTendenciaQuery } from '../../composables/queries/useMinhaTendenciaQuery';

import type { PeriodFilter } from '../../types/dashboard.types';

const { usaOrdemServico } = useOrdemServico();

const authStore = useAuthStore();
const { userData, isLoading: isLoadingUser } = storeToRefs(authStore);

const activePeriod = ref<PeriodFilter>('hoje');

const resumoQuery        = useMeuResumoQuery(activePeriod);
const tendenciaQuery     = useMinhaTendenciaQuery(activePeriod);
const vendasQuery        = useMinhasUltimasVendasQuery();
const filaQuery          = useMinhaFilaQuery();
const atrasadasQuery     = useMinhasOSAtrasadasQuery();
const retiradaQuery      = useOSAguardandoRetiradaQuery();

/**
 * As Ultimas Vendas aparecem em dois lugares do template (com e sem OS). Os
 * props ficam aqui para os dois nunca divergirem.
 */
const ultimasVendasProps = computed(() => ({
  vendas: minhasVendas.value,
  isLoading: vendasQuery.isLoading.value,
  isError: vendasQuery.isError.value,
  showTime: true,
}));
const atividadeQuery     = useMinhaAtividadeHojeQuery();

const periods: { id: PeriodFilter; label: string }[] = [
  { id: 'hoje', label: 'Hoje' },
  { id: 'semana', label: 'Semana' },
  { id: 'mes', label: 'Mês' },
];

const PERIOD_LABELS: Record<PeriodFilter, string> = {
  hoje: 'hoje',
  semana: 'esta semana',
  mes: 'este mês',
};

const saudacao = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return 'Bom dia';
  if (h < 18) return 'Boa tarde';
  return 'Boa noite';
});

const periodDescription = computed(
  () => `Veja seu desempenho pessoal para ${PERIOD_LABELS[activePeriod.value]}.`,
);

const d = computed(() => resumoQuery.data.value);

const cards = computed(() => [
  {
    id: 'minhas-vendas-valor',
    icon: TrendingUp,
    label: 'Minhas Vendas',
    value: d.value ? formatCurrency(d.value.minhas_vendas_valor) : 'R$ 0,00',
    isEmpty: !d.value || d.value.minhas_vendas_valor === 0,
    emptyLabel: 'Nenhuma venda ainda',
  },
  {
    id: 'minhas-vendas-count',
    icon: ShoppingCart,
    label: 'Qtd. Vendas',
    value: d.value ? String(d.value.minhas_vendas_count) : '0',
    isEmpty: !d.value || d.value.minhas_vendas_count === 0,
    emptyLabel: 'Nenhuma venda',
  },
  {
    id: 'minhas-os-abertas',
    icon: Wrench,
    label: 'OS em Andamento',
    value: d.value ? String(d.value.minhas_os_abertas) : '0',
    isEmpty: !d.value || d.value.minhas_os_abertas === 0,
    emptyLabel: 'Sem OS em aberto',
  },
  {
    id: 'minhas-os-concluidas',
    icon: CheckCircle,
    label: 'OS Concluídas',
    value: d.value ? String(d.value.minhas_os_concluidas) : '0',
    isEmpty: !d.value || d.value.minhas_os_concluidas === 0,
    emptyLabel: 'Nenhuma hoje ainda',
  },
]);

const osAtrasadas    = computed(() => atrasadasQuery.data.value?.items ?? []);
const totalAtrasadas = computed(() => atrasadasQuery.data.value?.total ?? 0);
const minhaFila      = computed(() => filaQuery.data.value?.items ?? []);
const minhasVendas   = computed(() => vendasQuery.data.value?.items ?? []);
const retirada       = computed(() => retiradaQuery.data.value?.items ?? []);
const atividade      = computed(() => atividadeQuery.data.value?.items ?? []);
</script>

<template>
  <div class="p-4 md:p-6 lg:p-8 space-y-5 md:space-y-6">

    <!-- Greeting -->
    <PageReview
      :title="`${saudacao}, ${userData?.nome}`"
      :description="periodDescription"
      :is-loading="isLoadingUser"
    />

    <!-- Banner OS Atrasadas (só aparece quando há) -->
    <OSAtrasadasBanner v-if="usaOrdemServico" :items="osAtrasadas" :total="totalAtrasadas" />

    <!-- Stats Section -->
    <div class="space-y-4">
      <div class="flex justify-end">
        <div class="flex bg-white p-1 rounded-xl border border-zinc-200 shadow-sm text-xs font-semibold">
          <button
            v-for="period in periods"
            :key="period.id"
            :class="[
              'px-3 md:px-4 py-1.5 md:py-2 rounded-lg transition-all duration-200',
              activePeriod === period.id
                ? 'bg-zinc-900 text-white shadow-sm'
                : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50',
            ]"
            @click="activePeriod = period.id"
          >
            {{ period.label }}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <template v-if="resumoQuery.isError.value">
          <div class="col-span-full bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-red-600 text-sm font-medium">
            Erro ao carregar métricas. Tente recarregar a página.
          </div>
        </template>

        <template v-else-if="resumoQuery.isLoading.value">
          <div
            v-for="i in 4"
            :key="i"
            class="bg-white p-5 md:p-6 rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm"
          >
            <div class="flex items-center justify-between mb-4">
              <div class="w-10 h-10 md:w-12 md:h-12 bg-zinc-100 rounded-xl md:rounded-2xl animate-pulse" />
            </div>
            <div class="w-20 h-3 bg-zinc-100 rounded animate-pulse mb-2" />
            <div class="w-28 h-7 bg-zinc-100 rounded animate-pulse" />
          </div>
        </template>

        <template v-else>
          <BaseStatsCard
            v-for="card in cards"
            :key="card.id"
            :icon="card.icon"
            :label="card.label"
            :value="card.value"
          >
            <template v-if="card.isEmpty" #badge>
              <span class="text-[10px] text-zinc-400 font-medium">{{ card.emptyLabel }}</span>
            </template>
          </BaseStatsCard>
        </template>
      </div>
    </div>

    <!-- Meu faturamento (número-herói) + minha tendência -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white p-5 md:p-6 rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm flex flex-col justify-center">
        <span class="text-[11px] md:text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Meu faturamento
        </span>
        <p class="mt-1 text-2xl md:text-3xl font-bold text-zinc-900 tabular-nums leading-none">
          {{ formatCurrency(d?.meu_faturamento ?? 0) }}
        </p>
        <div class="mt-3 text-xs text-zinc-500">
          Vendas <span class="font-semibold text-zinc-700">{{ formatCurrency(d?.minhas_vendas_valor ?? 0) }}</span>
          · Serviços <span class="font-semibold text-zinc-700">{{ formatCurrency(d?.minhas_os_valor ?? 0) }}</span>
        </div>
      </div>
      <div class="lg:col-span-2 bg-white p-4 md:p-5 rounded-2xl md:rounded-3xl border border-zinc-200 shadow-sm">
        <h3 class="text-sm font-bold text-zinc-700 mb-3">Minha tendência</h3>
        <div class="h-48 md:h-56">
          <TendenciaChart
            v-if="tendenciaQuery.data.value && tendenciaQuery.data.value.items.length"
            :por-dia="tendenciaQuery.data.value.items"
          />
          <div v-else class="h-full grid place-items-center text-xs text-zinc-400">
            Sem faturamento no período.
          </div>
        </div>
      </div>
    </div>

    <!--
      Linha 1: Minha Fila (3/5) + Últimas Vendas (2/5).

      SEM ORDEM DE SERVICO esta linha inteira desaparece e as Ultimas Vendas
      descem para a linha de baixo, ao lado da Atividade de Hoje. Manter a linha
      com o lado esquerdo vazio deixava a tela do operador — que numa adega e a
      mais usada do dia — com um buraco de 3/5 de largura logo no topo.
    -->
    <div v-if="usaOrdemServico" class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div class="lg:col-span-3">
        <MinhaFilaTable
          :items="minhaFila"
          :is-loading="filaQuery.isLoading.value"
          :is-error="filaQuery.isError.value"
        />
      </div>
      <div class="lg:col-span-2">
        <RecentTransactions v-bind="ultimasVendasProps" />
      </div>
    </div>

    <!-- Linha 2: OS Aguardando Retirada (2/5) + Atividade de Hoje (3/5) -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div class="lg:col-span-2">
        <OSAguardandoRetiradaTable v-if="usaOrdemServico"
          :items="retirada"
          :is-loading="retiradaQuery.isLoading.value"
          :is-error="retiradaQuery.isError.value"
        />
        <RecentTransactions v-else v-bind="ultimasVendasProps" />
      </div>
      <div class="lg:col-span-3">
        <AtividadeHoje
          :items="atividade"
          :is-loading="atividadeQuery.isLoading.value"
          :is-error="atividadeQuery.isError.value"
        />
      </div>
    </div>

  </div>
</template>
