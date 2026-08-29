<script setup lang="ts">
/**
 * O resultado do mês em regime de CAIXA.
 *
 * Chama-se "Resultado", nunca DRE: DRE é regime de competência, e um contador
 * que comparasse os dois acharia diferença legítima e abriria chamado. Aqui a
 * pergunta é a que o dono faz — entrou quanto, saiu quanto, sobrou quanto.
 */
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { ChevronLeft, ChevronRight, TrendingDown, TrendingUp, Wallet, AlertTriangle } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import { usePeriodoMes } from '../shared/composables/usePeriodoMes';
import { useResumoQuery } from '../shared/composables/useFinanceiro';

const router = useRouter();
const { range, rotulo, ehMesAtual, anterior, proximo } = usePeriodoMes();

const inicio = computed(() => range.value.inicio);
const fim = computed(() => range.value.fim);
const { data: resumo, isLoading } = useResumoQuery(inicio, fim);

// Um resultado negativo é informação, não erro — e é justamente o mês que o
// dono precisa enxergar. A cor muda; o número aparece do mesmo jeito.
const resultadoNegativo = computed(() => (resumo.value?.resultado ?? 0) < 0);

const maiorCategoria = computed(() => resumo.value?.despesas_por_categoria?.[0]?.total ?? 0);
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Seletor de mês -->
    <div class="flex items-center gap-3">
      <button
        type="button" @click="anterior"
        class="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer"
        aria-label="Mês anterior"
      >
        <ChevronLeft :size="18" class="text-gray-600" />
      </button>
      <span class="font-semibold text-gray-800 min-w-44 text-center">{{ rotulo }}</span>
      <button
        type="button" @click="proximo" :disabled="ehMesAtual"
        class="p-2 rounded-lg border border-gray-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-50 cursor-pointer"
        aria-label="Próximo mês"
      >
        <ChevronRight :size="18" class="text-gray-600" />
      </button>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <template v-else-if="resumo">
      <!-- Entrou / saiu / sobrou -->
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">
            <TrendingUp :size="15" class="text-emerald-500" /> Entrou
          </div>
          <p class="mt-2 text-2xl font-bold text-gray-800">{{ formatCurrency(resumo.faturamento) }}</p>
          <p class="mt-1 text-xs text-gray-400">Vendas e ordens de serviço finalizadas</p>
        </div>

        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">
            <TrendingDown :size="15" class="text-rose-500" /> Saiu
          </div>
          <p class="mt-2 text-2xl font-bold text-gray-800">{{ formatCurrency(resumo.despesas_pagas) }}</p>
          <p class="mt-1 text-xs text-gray-400">Contas efetivamente pagas no mês</p>
        </div>

        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="resultadoNegativo ? 'border-rose-200 bg-rose-50' : 'border-emerald-200 bg-emerald-50'"
        >
          <div class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
               :class="resultadoNegativo ? 'text-rose-600' : 'text-emerald-700'">
            <Wallet :size="15" /> Sobrou
          </div>
          <p class="mt-2 text-2xl font-bold" :class="resultadoNegativo ? 'text-rose-700' : 'text-emerald-800'">
            {{ formatCurrency(resumo.resultado) }}
          </p>
          <p class="mt-1 text-xs" :class="resultadoNegativo ? 'text-rose-500' : 'text-emerald-600'">
            {{ resultadoNegativo ? 'O mês fechou no vermelho' : 'Resultado do mês, em caixa' }}
          </p>
        </div>
      </div>

      <!-- Em aberto dos dois lados: o que ainda não entrou e o que ainda não saiu -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">A receber em aberto</p>
          <p class="mt-2 text-xl font-bold text-gray-800">{{ formatCurrency(resumo.a_receber_pendente) }}</p>
          <!-- Duas coisas que o card precisa dizer: ignora o mês visto (fiado
               vence lá na frente) e JÁ está dentro de "Entrou" — a venda
               fechou, o que não chegou foi o pagamento. Sem a linha, é somar
               duas vezes. -->
          <p class="mt-1 text-xs text-gray-400">De qualquer vencimento, já contado em Entrou</p>
        </div>
        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="resumo.a_receber_vencido > 0 ? 'border-rose-200 bg-rose-50' : 'border-gray-100 bg-white'"
        >
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
             :class="resumo.a_receber_vencido > 0 ? 'text-rose-600' : 'text-gray-500'">
            <AlertTriangle v-if="resumo.a_receber_vencido > 0" :size="14" /> A receber atrasado
          </p>
          <p class="mt-2 text-xl font-bold" :class="resumo.a_receber_vencido > 0 ? 'text-rose-700' : 'text-gray-800'">
            {{ formatCurrency(resumo.a_receber_vencido) }}
          </p>
        </div>
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">A pagar em aberto</p>
          <p class="mt-2 text-xl font-bold text-gray-800">{{ formatCurrency(resumo.a_pagar_pendente) }}</p>
        </div>
        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="resumo.a_pagar_vencido > 0 ? 'border-amber-200 bg-amber-50' : 'border-gray-100 bg-white'"
        >
          <!-- "A pagar vencido", e não só "Vencido": com o card do receber ao
               lado, um rótulo solto deixa de dizer de quem é a dívida. -->
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
             :class="resumo.a_pagar_vencido > 0 ? 'text-amber-700' : 'text-gray-500'">
            <AlertTriangle v-if="resumo.a_pagar_vencido > 0" :size="14" /> A pagar vencido
          </p>
          <p class="mt-2 text-xl font-bold" :class="resumo.a_pagar_vencido > 0 ? 'text-amber-800' : 'text-gray-800'">
            {{ formatCurrency(resumo.a_pagar_vencido) }}
          </p>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Para onde o dinheiro foi -->
        <section class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 class="text-sm font-bold text-gray-800">Para onde o dinheiro foi</h3>
          <p v-if="!resumo.despesas_por_categoria.length" class="mt-3 text-sm text-gray-400">
            Nenhuma conta paga neste mês.
          </p>
          <ul v-else class="mt-4 flex flex-col gap-3">
            <li v-for="c in resumo.despesas_por_categoria" :key="c.nome">
              <div class="flex items-baseline justify-between gap-3 text-sm">
                <span class="text-gray-700">{{ c.nome }}</span>
                <span class="font-semibold text-gray-800 tabular-nums">{{ formatCurrency(c.total) }}</span>
              </div>
              <!-- Barra proporcional à MAIOR categoria, não ao total: com uma
                   categoria dominante, todas as outras viram fios invisíveis. -->
              <div class="mt-1 h-1.5 w-full rounded-full bg-gray-100">
                <div
                  class="h-1.5 rounded-full bg-brand-primary"
                  :style="{ width: `${maiorCategoria ? (c.total / maiorCategoria) * 100 : 0}%` }"
                />
              </div>
            </li>
          </ul>
        </section>

        <!-- Próximas a vencer -->
        <section class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-gray-800">Vencendo em breve</h3>
            <button
              type="button" class="text-xs font-semibold text-brand-primary cursor-pointer"
              @click="router.push({ name: 'finance-payable' })"
            >
              Ver todas
            </button>
          </div>
          <p v-if="!resumo.proximas_a_vencer.length" class="mt-3 text-sm text-gray-400">
            Nada vencendo nos próximos dias.
          </p>
          <ul v-else class="mt-4 flex flex-col divide-y divide-gray-100">
            <li v-for="conta in resumo.proximas_a_vencer" :key="conta.id" class="flex items-center justify-between gap-3 py-2.5">
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-gray-800">{{ conta.descricao }}</p>
                <p class="text-xs" :class="conta.vencida ? 'text-rose-600 font-semibold' : 'text-gray-400'">
                  {{ conta.vencida ? 'Venceu em' : 'Vence em' }} {{ formatDataPura(conta.vencimento) }}
                </p>
              </div>
              <span class="shrink-0 text-sm font-semibold text-gray-800 tabular-nums">
                {{ formatCurrency(conta.valor) }}
              </span>
            </li>
          </ul>
        </section>
      </div>
    </template>
  </div>
</template>
