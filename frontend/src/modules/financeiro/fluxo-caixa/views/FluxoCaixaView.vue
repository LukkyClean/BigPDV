<script setup lang="ts">
/**
 * O Fluxo de Caixa: o que está AGENDADO para acontecer.
 *
 * Não é o extrato do que passou — isso é a Visão Geral. Aqui cada linha nasce
 * de um documento em aberto, no dia do vencimento, e a régua acumula o saldo
 * dia a dia a partir do que o dono declarou ter hoje.
 *
 * A tela existe para responder UMA pergunta: "em que dia o dinheiro acaba?".
 * Por isso o aviso do primeiro dia negativo vem antes da lista — quem já sabe
 * a resposta não precisa ler o resto.
 *
 * As janelas param em 90 dias (o teto do backend) porque é até onde a loja tem
 * documento lançado: além disso a linha viraria uma reta, e uma projeção que
 * não tem de onde tirar número não é projeção, é palpite.
 */
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { AlertTriangle, CalendarClock, TrendingDown, TrendingUp, Wallet } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import SaldoContasModal from '../components/SaldoContasModal.vue';
import { useFluxoCaixaQuery } from '../../shared/composables/useFinanceiro';

const router = useRouter();

const dias = ref(30);
const modalSaldo = ref(false);

const { data: fluxo, isLoading } = useFluxoCaixaQuery(dias);

const temAtraso = computed(
  () => (fluxo.value?.atrasado_a_pagar ?? 0) > 0 || (fluxo.value?.atrasado_a_receber ?? 0) > 0,
);

/**
 * Há quantos dias o saldo foi declarado.
 *
 * Data pura montada campo a campo: `new Date('2026-09-27')` é lido como UTC e,
 * no fuso da loja, volta um dia — o mesmo erro que já custou caro no relatório.
 */
const diasDesdeSaldo = computed(() => {
  const iso = fluxo.value?.saldo_informado_em;
  if (!iso) return null;
  const [ano, mes, dia] = iso.split('-').map(Number);
  const informado = new Date(ano, mes - 1, dia);
  const hoje = new Date();
  return Math.floor(
    (new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate()).getTime() -
      informado.getTime()) /
      86400000,
  );
});

// Uma semana é o ponto em que o retrato deixa de servir: nele já couberam um
// fim de semana de vendas e as contas do começo do mês.
const saldoVelho = computed(() => (diasDesdeSaldo.value ?? 0) >= 7);

function diaSemana(iso: string): string {
  const [ano, mes, dia] = iso.split('-').map(Number);
  return new Date(ano, mes - 1, dia).toLocaleDateString('pt-BR', { weekday: 'short' });
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Janela -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <button
          v-for="opcao in [30, 60, 90]"
          :key="opcao"
          type="button"
          class="rounded-lg border px-3.5 py-1.5 text-sm font-semibold cursor-pointer"
          :class="
            dias === opcao
              ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          "
          @click="dias = opcao"
        >
          {{ opcao }} dias
        </button>
      </div>

      <BaseButton variant="secondary" class="px-4" @click="modalSaldo = true">
        <Wallet :size="16" class="mr-2" /> Atualizar saldo
      </BaseButton>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <template v-else-if="fluxo">
      <!-- Sem saldo declarado a projeção não parte de lugar nenhum. "Não sei"
           não é zero, e desenhar a linha assim mesmo faria o dono ler o
           resultado como se fosse o dinheiro dele. -->
      <div
        v-if="!fluxo.saldo_declarado"
        class="rounded-2xl border border-amber-200 bg-amber-50 p-5"
      >
        <p class="flex items-center gap-2 text-sm font-bold text-amber-800">
          <AlertTriangle :size="16" /> Falta dizer quanto você tem hoje
        </p>
        <p class="mt-1.5 text-sm text-amber-700">
          A projeção soma e subtrai a partir do seu saldo de hoje, e esse número só você tem —
          o sistema não consegue calculá-lo sozinho. Enquanto não informar, a linha abaixo
          mostra só o movimento previsto.
        </p>
        <BaseButton variant="primary" class="mt-3 px-4" @click="modalSaldo = true">
          Informar saldo
        </BaseButton>
      </div>

      <!-- O dia em que o dinheiro acaba: a resposta vem antes da lista. -->
      <div
        v-else-if="fluxo.primeiro_dia_negativo"
        class="rounded-2xl border border-rose-200 bg-rose-50 p-5"
      >
        <p class="flex items-center gap-2 text-sm font-bold text-rose-800">
          <AlertTriangle :size="16" /> O dinheiro acaba em
          {{ formatDataPura(fluxo.primeiro_dia_negativo) }}
        </p>
        <p class="mt-1.5 text-sm text-rose-700">
          Nesse dia o saldo previsto fica negativo, e o fundo do poço é
          <strong>{{ formatCurrency(fluxo.menor_saldo) }}</strong>
          <template v-if="fluxo.menor_saldo_em">
            em {{ formatDataPura(fluxo.menor_saldo_em) }}</template
          >. Dá para adiar uma conta, cobrar um fiado ou reforçar o caixa até lá.
        </p>
      </div>

      <!-- Saldo hoje / vai entrar / vai sair / sobra prevista -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            <Wallet :size="15" class="text-gray-400" /> Saldo hoje
          </p>
          <p class="mt-2 text-xl font-bold text-gray-800">
            {{ formatCurrency(fluxo.saldo_inicial) }}
          </p>
          <p v-if="fluxo.saldo_declarado" class="mt-1 text-xs" :class="saldoVelho ? 'text-amber-600 font-semibold' : 'text-gray-400'">
            <template v-if="diasDesdeSaldo === 0">Informado hoje</template>
            <template v-else-if="diasDesdeSaldo === 1">Informado ontem</template>
            <template v-else>Informado há {{ diasDesdeSaldo }} dias — confira</template>
          </p>
          <p v-else class="mt-1 text-xs text-amber-600 font-semibold">Você ainda não informou</p>
        </div>

        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            <TrendingUp :size="15" class="text-emerald-500" /> Vai entrar
          </p>
          <p class="mt-2 text-xl font-bold text-gray-800">
            {{ formatCurrency(fluxo.total_entradas) }}
          </p>
          <p class="mt-1 text-xs text-gray-400">Cobranças com vencimento no período</p>
        </div>

        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            <TrendingDown :size="15" class="text-rose-500" /> Vai sair
          </p>
          <p class="mt-2 text-xl font-bold text-gray-800">
            {{ formatCurrency(fluxo.total_saidas) }}
          </p>
          <p class="mt-1 text-xs text-gray-400">Contas a pagar no mesmo período</p>
        </div>

        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="fluxo.saldo_final < 0 ? 'border-rose-200 bg-rose-50' : 'border-emerald-200 bg-emerald-50'"
        >
          <p
            class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
            :class="fluxo.saldo_final < 0 ? 'text-rose-600' : 'text-emerald-700'"
          >
            <!-- Sem saldo declarado isto não é sobra, é o movimento líquido do
                 período — que continua sendo informação boa ("vai sair mais do
                 que entra"), mas com outro nome. -->
            <CalendarClock :size="15" />
            {{ fluxo.saldo_declarado ? `Sobra em ${formatDataPura(fluxo.fim)}` : 'Movimento no período' }}
          </p>
          <p
            class="mt-2 text-xl font-bold"
            :class="fluxo.saldo_final < 0 ? 'text-rose-700' : 'text-emerald-800'"
          >
            {{ formatCurrency(fluxo.saldo_final) }}
          </p>
          <p class="mt-1 text-xs" :class="fluxo.saldo_final < 0 ? 'text-rose-500' : 'text-emerald-600'">
            {{
              fluxo.saldo_declarado
                ? 'Saldo previsto no fim do período'
                : 'O que entra menos o que sai, sem saldo de partida'
            }}
          </p>
        </div>
      </div>

      <!-- O atrasado fica FORA da régua: não tem dia futuro para ocupar, e
           empurrá-lo para hoje inventaria um aperto que talvez não exista. -->
      <div
        v-if="temAtraso"
        class="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-2xl border border-gray-100 bg-white px-5 py-4 shadow-sm"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Fora da projeção</p>
        <button
          v-if="fluxo.atrasado_a_receber > 0"
          type="button"
          class="text-sm text-gray-700 cursor-pointer hover:underline"
          @click="router.push({ name: 'finance-receivable' })"
        >
          <strong class="text-rose-600">{{ formatCurrency(fluxo.atrasado_a_receber) }}</strong>
          atrasado a receber
        </button>
        <button
          v-if="fluxo.atrasado_a_pagar > 0"
          type="button"
          class="text-sm text-gray-700 cursor-pointer hover:underline"
          @click="router.push({ name: 'finance-payable' })"
        >
          <strong class="text-amber-700">{{ formatCurrency(fluxo.atrasado_a_pagar) }}</strong>
          atrasado a pagar
        </button>
        <p class="text-xs text-gray-400">
          Vencido não entra na linha do tempo — não há dia futuro para ele ocupar.
        </p>
      </div>

      <!-- A régua -->
      <section class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-gray-800">Dia a dia</h3>

        <p v-if="!fluxo.linha.length" class="mt-3 text-sm text-gray-400">
          Nada agendado para os próximos {{ fluxo.dias }} dias. Contas a pagar e cobranças a
          receber aparecem aqui na data do vencimento.
        </p>

        <!-- Cabeçalho das DUAS colunas de número. Sem ele, "no dia" e
             "acumulado" ficam lado a lado sem dizer o que são, e o acumulado é
             lido como o movimento do dia — foi exatamente onde o primeiro uso
             real tropeçou. -->
        <div
          v-else
          class="mt-4 flex items-baseline justify-between gap-3 border-b border-gray-100 pb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400"
        >
          <span>Dia</span>
          <div class="flex items-baseline gap-4">
            <span class="min-w-32 text-right">No dia</span>
            <span class="min-w-28 text-right">
              {{ fluxo.saldo_declarado ? 'Saldo previsto' : 'Acumulado' }}
            </span>
          </div>
        </div>

        <ul v-if="fluxo.linha.length" class="flex flex-col divide-y divide-gray-100">
          <li v-for="dia in fluxo.linha" :key="dia.data" class="py-3">
            <div class="flex items-baseline justify-between gap-3">
              <p class="text-sm font-semibold text-gray-800">
                {{ formatDataPura(dia.data) }}
                <span class="ml-1 text-xs font-normal capitalize text-gray-400">
                  {{ diaSemana(dia.data) }}
                </span>
              </p>
              <div class="flex items-baseline gap-4 text-sm tabular-nums">
                <span class="flex min-w-32 justify-end gap-3">
                  <span v-if="dia.entradas > 0" class="text-emerald-600">
                    +{{ formatCurrency(dia.entradas) }}
                  </span>
                  <span v-if="dia.saidas > 0" class="text-rose-600">
                    −{{ formatCurrency(dia.saidas) }}
                  </span>
                </span>
                <!-- O acumulado é o número que responde a pergunta da tela; por
                     isso é o mais forte da linha.
                     SEM SALDO DECLARADO ele não é dinheiro, é só a soma do
                     movimento — e aí não se pinta de vermelho, senão um dia
                     tranquilo aparece como se a loja estivesse quebrada. -->
                <span
                  class="min-w-28 text-right font-bold"
                  :class="
                    !fluxo.saldo_declarado
                      ? 'text-gray-400'
                      : dia.saldo < 0
                        ? 'text-rose-700'
                        : 'text-gray-800'
                  "
                >
                  {{ formatCurrency(dia.saldo) }}
                </span>
              </div>
            </div>

            <ul class="mt-1.5 flex flex-col gap-0.5">
              <li
                v-for="lancamento in dia.lancamentos"
                :key="`${lancamento.tipo}-${lancamento.conta_id}`"
                class="flex items-baseline justify-between gap-3 text-xs text-gray-500"
              >
                <span class="truncate">{{ lancamento.descricao }}</span>
                <span class="shrink-0 tabular-nums">
                  {{ lancamento.tipo === 'ENTRADA' ? '+' : '−' }}{{ formatCurrency(lancamento.valor) }}
                </span>
              </li>
            </ul>
          </li>
        </ul>

        <p v-if="fluxo.linha.length && !fluxo.saldo_declarado" class="mt-3 text-xs text-gray-400">
          Sem saldo informado, a coluna da direita soma só o movimento a partir de zero — não
          é o seu dinheiro. Informe o saldo para ela virar o saldo previsto de cada dia.
        </p>
      </section>
    </template>

    <SaldoContasModal :aberto="modalSaldo" @fechar="modalSaldo = false" />
  </div>
</template>
