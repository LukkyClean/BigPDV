<script setup lang="ts">
/**
 * Conciliação: conferir o que a operadora depositou contra o que a loja espera.
 *
 * A tela é organizada por DIA, e não por venda, porque é assim que o dinheiro
 * chega — a operadora não deposita venda a venda, deposita o lote do dia, um
 * valor só. Conferir item a item contra o extrato é exatamente o trabalho que
 * esta tela existe para evitar.
 *
 * NÃO importa arquivo da operadora (CSV/OFX). Cada credenciadora tem o seu
 * formato, e adivinhar layout sem um extrato real na mão seria chute — quando
 * houver um arquivo de verdade, ele entra por cima disto, alimentando o mesmo
 * "quanto caiu".
 */
import { computed, ref } from 'vue';
import { ChevronLeft, ChevronRight, CheckCircle2, CreditCard } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import ConferirDepositoModal from '../components/ConferirDepositoModal.vue';
import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import { useConciliacaoQuery } from '../../shared/composables/useFinanceiro';
import type { ConciliacaoDia } from '../../shared/schemas/financeiro.schema';

const { range, rotulo, ehMesAtual, anterior, proximo } = usePeriodoMes();

const inicio = computed(() => range.value.inicio);
const fim = computed(() => range.value.fim);
const { data: conciliacao, isLoading } = useConciliacaoQuery(inicio, fim);

const diaEmConferencia = ref<ConciliacaoDia | null>(null);

const hojeIso = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
});

// Depósito que já deveria ter caído é o que vale a pena conferir primeiro; o
// que vence semana que vem ainda não tem extrato para comparar.
function jaVenceu(data: string): boolean {
  return data <= hojeIso.value;
}
</script>

<template>
  <div class="flex flex-col gap-6 md:gap-8">
    <!-- Cabecalho da secao. Mesmo padrao de Clientes e Produtos:
         PageReview a esquerda, acao principal a direita. -->
    <div class="flex items-center justify-between gap-4">
      <PageReview title="Conciliação de Cartão" description="O extrato da operadora conferido contra a loja" />
    </div>

    <!-- Seletor de mês, o mesmo das outras telas do módulo -->
    <div class="flex items-center gap-3">
      <button
        type="button" @click="anterior"
        class="p-2 rounded-lg border border-zinc-200 hover:bg-zinc-50 cursor-pointer"
        aria-label="Mês anterior"
      >
        <ChevronLeft :size="18" class="text-zinc-600" />
      </button>
      <span class="font-semibold text-zinc-800 min-w-44 text-center">{{ rotulo }}</span>
      <button
        type="button" @click="proximo" :disabled="ehMesAtual"
        class="p-2 rounded-lg border border-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-50 cursor-pointer"
        aria-label="Próximo mês"
      >
        <ChevronRight :size="18" class="text-zinc-600" />
      </button>
    </div>

    <div v-if="isLoading" class="text-sm text-zinc-500">Carregando…</div>

    <template v-else-if="conciliacao">
      <div class="rounded-2xl border border-zinc-100 bg-white p-5 shadow-sm">
        <p class="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          A conferir no período
        </p>
        <p class="mt-2 text-2xl font-bold text-zinc-800">
          {{ formatCurrency(conciliacao.total_previsto) }}
        </p>
        <p class="mt-1 text-xs text-zinc-400">
          Cobranças em aberto, agrupadas pelo dia em que o dinheiro deve entrar
        </p>
      </div>

      <div
        v-if="!conciliacao.dias.length"
        class="rounded-2xl border border-zinc-100 bg-white p-8 text-center shadow-sm"
      >
        <CheckCircle2 :size="28" class="mx-auto text-emerald-500" />
        <p class="mt-3 text-sm font-semibold text-zinc-800">Nada a conferir neste mês</p>
        <p class="mt-1 text-sm text-zinc-500">
          Cobranças com data de repasse aparecem aqui — cartão a receber, boleto, cheque, fiado.
        </p>
      </div>

      <div v-else class="flex flex-col gap-4">
        <section
          v-for="dia in conciliacao.dias"
          :key="dia.data"
          class="rounded-2xl border bg-white p-5 shadow-sm"
          :class="jaVenceu(dia.data) ? 'border-amber-200' : 'border-zinc-100'"
        >
          <div class="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <p class="text-sm font-bold text-zinc-800">
                {{ formatDataPura(dia.data) }}
                <span
                  v-if="jaVenceu(dia.data)"
                  class="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700"
                >
                  já deveria ter caído
                </span>
              </p>
              <p class="mt-0.5 text-xs text-zinc-500">
                {{ dia.quantidade }} cobrança(s) · previsto
                <strong class="text-zinc-700">{{ formatCurrency(dia.total_previsto) }}</strong>
              </p>
            </div>

            <BaseButton variant="secondary" class="px-4" @click="diaEmConferencia = dia">
              Conferir depósito
            </BaseButton>
          </div>

          <ul class="mt-4 flex flex-col divide-y divide-zinc-100">
            <li
              v-for="item in dia.itens"
              :key="item.conta_id"
              class="flex items-baseline justify-between gap-3 py-2"
            >
              <div class="min-w-0">
                <p class="truncate text-sm text-zinc-700">{{ item.descricao }}</p>
                <p class="flex items-center gap-1.5 text-xs text-zinc-400">
                  <template v-if="item.forma_origem">
                    <CreditCard :size="12" /> {{ item.forma_origem }}
                  </template>
                  <template v-else>Lançada à mão</template>
                  <template v-if="item.cliente_nome"> · {{ item.cliente_nome }}</template>
                </p>
              </div>
              <span class="shrink-0 text-sm font-semibold text-zinc-800 tabular-nums">
                {{ formatCurrency(item.valor) }}
              </span>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <ConferirDepositoModal :dia="diaEmConferencia" @fechar="diaEmConferencia = null" />
  </div>
</template>
