<script setup lang="ts">
/**
 * O mês em dois blocos: o LUCRO e o CAIXA.
 *
 * Nunca se chama DRE: DRE é regime de competência, e um contador que comparasse
 * os dois acharia diferença legítima e abriria chamado.
 *
 * São dois blocos porque são duas perguntas, e as duas são do dono:
 *   "ganhei dinheiro?"     faturado − custo do que vendeu − despesas
 *   "sobrou na gaveta?"    entrou no caixa − saiu do caixa
 *
 * Elas divergem por motivo legítimo (fiado entra no lucro e não no caixa;
 * compra de estoque sai do caixa e não do lucro), e mostrar só uma delas foi
 * exatamente o defeito que esta tela tinha: até 02/09/2026 o custo da peça não
 * aparecia em lugar nenhum, e um serviço de R$ 160 com peça de R$ 60 comprada
 * na hora saía como R$ 160 de lucro.
 */
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  ChevronLeft,
  ChevronRight,
  Package,
  TrendingDown,
  TrendingUp,
  Wallet,
  AlertTriangle,
} from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import { useOrdemServico } from '@/shared/composables/useOrdemServico';

import PainelAtencao from '../shared/components/PainelAtencao.vue';
import SaldoContasModal from '../fluxo-caixa/components/SaldoContasModal.vue';
import { usePeriodoMes } from '../shared/composables/usePeriodoMes';
import { useResumoQuery } from '../shared/composables/useFinanceiro';

const router = useRouter();
const { range, rotulo, ehMesAtual, anterior, proximo } = usePeriodoMes();
// Numa loja sem OS, prometer "ordens de serviço" no card faz o dono procurar
// um módulo que ele não tem.
const { usaOrdemServico } = useOrdemServico();

// O alerta de saldo resolve NA HORA, aqui mesmo: mandar o dono para a tela de
// Fluxo de Caixa só para clicar em "Atualizar saldo" seria uma volta inteira
// para digitar um número.
const modalSaldo = ref(false);

const inicio = computed(() => range.value.inicio);
const fim = computed(() => range.value.fim);
const { data: resumo, isLoading } = useResumoQuery(inicio, fim);

// Um resultado negativo é informação, não erro — e é justamente o mês que o
// dono precisa enxergar. A cor muda; o número aparece do mesmo jeito.
const resultadoNegativo = computed(() => (resumo.value?.resultado ?? 0) < 0);

const maiorCategoria = computed(() => resumo.value?.despesas_por_categoria?.[0]?.total ?? 0);

/**
 * Quanto do faturado ainda não passou pelo caixa.
 *
 * Positivo é o caso normal de quem vende a prazo. Pode dar NEGATIVO, e isso
 * também é certo: um mês em que entrou muito fiado antigo recebe mais dinheiro
 * do que faturou. Por isso o texto muda de lado em vez de esconder o sinal.
 */
const diferencaCaixa = computed(
  () => (resumo.value?.faturamento ?? 0) - (resumo.value?.entrou_caixa ?? 0),
);
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
      <!-- Antes dos números, de propósito: quem abre a tela com um problema
           precisa ver o problema, não descobrir sozinho lendo seis cards. -->
      <PainelAtencao :alertas="resumo.alertas" @informar-saldo="modalSaldo = true" />
      <!-- Faturado / custo / despesas / lucro -->
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">
            <TrendingUp :size="15" class="text-emerald-500" /> Faturado
          </div>
          <p class="mt-2 text-2xl font-bold text-gray-800">{{ formatCurrency(resumo.faturamento) }}</p>
          <p class="mt-1 text-xs text-gray-400">
            {{ usaOrdemServico ? 'Vendas e ordens de serviço finalizadas' : 'Vendas finalizadas' }}
          </p>

          <!-- A SEGUNDA LEITURA do mesmo mês, e não um pedaço da primeira.
               "Faturado" é o que a loja vendeu; "entrou de fato" é o dinheiro
               que passou pelo caixa, venha da venda de hoje ou do fiado do mês
               passado. Mostrar os dois é o que impede a tela de prometer
               dinheiro que ainda está na rua. -->
          <div class="mt-3 border-t border-gray-100 pt-3">
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-xs text-gray-500">Entrou de fato</span>
              <span class="text-sm font-bold text-gray-800 tabular-nums">
                {{ formatCurrency(resumo.entrou_caixa) }}
              </span>
            </div>
            <p v-if="diferencaCaixa > 0" class="mt-1 text-xs text-amber-600">
              {{ formatCurrency(diferencaCaixa) }} faturado ainda não passou pelo caixa
            </p>
            <p v-else-if="diferencaCaixa < 0" class="mt-1 text-xs text-emerald-600">
              {{ formatCurrency(-diferencaCaixa) }} a mais que o faturado — cobrança de
              outros meses entrando
            </p>
            <p v-else class="mt-1 text-xs text-gray-400">Tudo que foi faturado entrou.</p>
          </div>
        </div>

        <!-- O CUSTO DO QUE FOI VENDIDO. Card próprio, e não uma linha escondida
             dentro de "Saiu": é o gasto que o dono mais sente e o que menos
             aparecia — até 02/09/2026 ele não estava em lugar nenhum desta
             tela, e um serviço de R$ 160 com peça de R$ 60 saía como R$ 160 de
             lucro. -->
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">
            <Package :size="15" class="text-amber-500" /> Custo do que vendeu
          </div>
          <p class="mt-2 text-2xl font-bold text-gray-800">
            {{ formatCurrency(resumo.custo_mercadorias) }}
          </p>
          <p class="mt-1 text-xs text-gray-400">
            {{ usaOrdemServico ? 'Peças e produtos que saíram nas vendas e OS' : 'Produtos que saíram nas vendas' }}
          </p>
          <!-- A confiança do número, não o número. Saída de estoque sem custo
               conhecido faz o CMV sair menor do que foi, e um custo subestimado
               em silêncio vira lucro inventado. -->
          <p v-if="resumo.custo_sem_registro > 0" class="mt-2 text-xs text-amber-600">
            {{ resumo.custo_sem_registro }}
            {{ resumo.custo_sem_registro === 1 ? 'saída saiu' : 'saídas saíram' }} sem custo
            cadastrado — o custo real é maior que este.
          </p>
        </div>

        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">
            <TrendingDown :size="15" class="text-rose-500" /> Despesas
          </div>
          <p class="mt-2 text-2xl font-bold text-gray-800">{{ formatCurrency(resumo.despesas_pagas) }}</p>
          <p class="mt-1 text-xs text-gray-400">Contas pagas no mês: aluguel, luz, salário…</p>
          <!-- Compra de mercadoria saiu do caixa mas NÃO é despesa: virou
               estoque. Ela precisa aparecer (o dinheiro saiu mesmo) sem entrar
               na conta do lucro, senão a mesma peça é descontada duas vezes —
               uma aqui e outra no card do custo. -->
          <p v-if="resumo.compras_estoque > 0" class="mt-2 text-xs text-gray-500">
            + {{ formatCurrency(resumo.compras_estoque) }} em compra de mercadoria, que virou
            estoque e só entra no lucro quando for vendida.
          </p>
        </div>

        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="resultadoNegativo ? 'border-rose-200 bg-rose-50' : 'border-emerald-200 bg-emerald-50'"
        >
          <div class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
               :class="resultadoNegativo ? 'text-rose-600' : 'text-emerald-700'">
            <Wallet :size="15" /> Lucro
          </div>
          <p class="mt-2 text-2xl font-bold" :class="resultadoNegativo ? 'text-rose-700' : 'text-emerald-800'">
            {{ formatCurrency(resumo.resultado) }}
          </p>
          <!-- A conta escrita por extenso. O dono precisa poder refazê-la de
               cabeça: um número de lucro que ninguém consegue conferir é um
               número em que ninguém confia. -->
          <p class="mt-1 text-xs" :class="resultadoNegativo ? 'text-rose-500' : 'text-emerald-600'">
            Faturado − custo do que vendeu − despesas
          </p>
          <p v-if="resultadoNegativo" class="mt-1 text-xs font-semibold text-rose-500">
            O mês fechou no vermelho
          </p>
        </div>
      </div>

      <!-- A OUTRA PERGUNTA, e por isso uma faixa à parte e não um quarto card:
           "ganhei dinheiro?" e "sobrou dinheiro na gaveta?" são coisas
           diferentes, e num mês de muito fiado elas discordam de propósito. -->
      <div class="rounded-2xl border border-gray-100 bg-white px-5 py-4 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">
            No caixa, neste mês
          </p>
          <div class="flex flex-wrap items-baseline gap-x-6 gap-y-1 text-sm">
            <span class="text-gray-500">
              Entrou <strong class="text-gray-800 tabular-nums">{{ formatCurrency(resumo.entrou_caixa) }}</strong>
            </span>
            <span class="text-gray-500">
              Saiu <strong class="text-gray-800 tabular-nums">{{ formatCurrency(resumo.saiu_caixa) }}</strong>
            </span>
            <span :class="resumo.sobrou_caixa < 0 ? 'text-rose-600' : 'text-emerald-700'">
              Sobrou
              <strong class="tabular-nums">{{ formatCurrency(resumo.sobrou_caixa) }}</strong>
            </span>
          </div>
        </div>
        <p class="mt-1.5 text-xs text-gray-400">
          Dinheiro que andou, não lucro: a venda fiado de hoje entra no lucro e não aqui, e a
          compra de estoque sai daqui e não do lucro.
        </p>
      </div>

      <!-- O livro do dinheiro só passou a receber venda e OS sem caixa aberto em
           29/08/2026. Antes disso ele é incompleto, e "entrou de fato" aparece
           menor do que foi. Dizer isso é obrigatório enquanto houver mês antigo
           na tela: sem o aviso, o dono conclui que sumiu dinheiro. -->
      <p class="-mt-3 text-xs text-gray-400">
        "Entrou de fato" vem do livro do dinheiro, que passou a registrar toda venda e OS em
        29/08/2026. Em meses anteriores a essa data ele aparece menor do que realmente entrou.
      </p>

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

    <SaldoContasModal :aberto="modalSaldo" @fechar="modalSaldo = false" />
  </div>
</template>
