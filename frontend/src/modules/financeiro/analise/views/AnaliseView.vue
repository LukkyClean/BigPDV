<script setup lang="ts">
/**
 * Análise: para onde o negócio está indo.
 *
 * O resto do módulo responde "como está agora" — esta tela responde "em que
 * direção". É o papel que o dono pagaria a um consultor para cumprir: olhar a
 * série e dizer o que mudou.
 *
 * A REGRA QUE ATRAVESSA A TELA INTEIRA É O PORTÃO DE HISTÓRICO. Cada leitura
 * declara quantos meses FECHADOS exige e, abaixo disso, não aparece torta nem
 * aparece vazia: aparece dizendo o que falta e quando vai existir. Dois pontos
 * fazem qualquer reta, e um número inventado aqui vira decisão errada lá na
 * loja.
 *
 * O mês corrente não está em lugar nenhum daqui — quem mostra o mês em
 * andamento é a Visão Geral.
 */
import { computed, ref } from 'vue';
import { CalendarRange, LineChart, Percent, TrendingUp, Wallet } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';

import SerieBarras from '../components/SerieBarras.vue';
import { useProjecaoQuery, useSerieQuery } from '../../shared/composables/useFinanceiro';

// Quantos meses fechados cada leitura exige. Os números vêm do plano e são a
// razão de a tela não mentir no primeiro mês de uso.
const PORTAO_COMPARACAO = 2;
const PORTAO_MEDIA = 3;

// Faixa em que a variação é "na média". Abaixo de 10% para cima ou para baixo,
// mês de loja pequena oscila por acaso — chamar isso de tendência ensinaria o
// dono a ignorar a tela.
const FAIXA_NA_MEDIA = 0.1;

const meses = ref(12);
const { data: serie, isLoading } = useSerieQuery(meses);
const { data: projecao } = useProjecaoQuery();

const disponiveis = computed(() => serie.value?.meses_disponiveis ?? 0);
const historico = computed(() => serie.value?.meses ?? []);

/**
 * O último mês FECHADO — o mês de que esta tela fala.
 *
 * Índice em vez de `.at(-1)`: o alvo de TypeScript do projeto é anterior ao
 * ES2022, e mudar o `tsconfig` inteiro por causa de duas linhas seria mexer em
 * todo mundo para resolver o meu problema.
 */
const ultimo = computed(() => historico.value[historico.value.length - 1] ?? null);
const anterior = computed(() => historico.value[historico.value.length - 2] ?? null);

function nomeDoMes(mes?: string | null): string {
  if (!mes) return '';
  const [ano, m] = mes.split('-');
  const nomes = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  return `${nomes[Number(m) - 1]} de ${ano}`;
}

/** Média da receita dos meses ANTERIORES ao último (até 3). */
const mediaAnterior = computed(() => {
  const anteriores = historico.value.slice(-4, -1);
  if (!anteriores.length) return null;
  return Math.round(anteriores.reduce((s, m) => s + m.receita, 0) / anteriores.length);
});

const variacao = computed(() => {
  if (!ultimo.value || !anterior.value || !anterior.value.receita) return null;
  return (ultimo.value.receita - anterior.value.receita) / anterior.value.receita;
});

/**
 * O rótulo, que é o que decide — não o número.
 *
 * É o insight que o Xero usa nos benchmarks de setor: "R$ 8.400" não diz nada;
 * "abaixo da sua média" diz. A diferença é que o nosso par de comparação é a
 * própria loja no passado, não o setor.
 */
const rotuloMedia = computed(() => {
  // O PORTÃO, cobrado aqui e não só no texto: com dois meses fechados a média
  // seria de UM mês, e "acima da sua média" viraria "acima do mês passado" com
  // outro nome — dito com uma confiança que o dado não tem.
  if (disponiveis.value < PORTAO_MEDIA) return null;
  if (mediaAnterior.value === null || !ultimo.value) return null;
  if (!mediaAnterior.value) return null;
  const razao = (ultimo.value.receita - mediaAnterior.value) / mediaAnterior.value;
  if (razao > FAIXA_NA_MEDIA) return { texto: 'acima da sua média', cor: 'text-emerald-600' };
  if (razao < -FAIXA_NA_MEDIA) return { texto: 'abaixo da sua média', cor: 'text-rose-600' };
  return { texto: 'na média dos últimos meses', cor: 'text-gray-500' };
});

/** A origem que mais pesou no último mês — "dependo de uma perna só?". */
const concentracao = computed(() => {
  const mes = ultimo.value;
  if (!mes || !mes.receita || mes.origens.length < 2) return null;
  const maior = [...mes.origens].sort((a, b) => b.total - a.total)[0];
  return { rotulo: maior.rotulo, fatia: Math.round((maior.total / mes.receita) * 100) };
});

const prazo = computed(() => ultimo.value?.prazo_medio_recebimento ?? null);

/** Quantos meses faltam para uma leitura destravar. */
function faltam(portao: number): number {
  return Math.max(0, portao - disponiveis.value);
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex items-center gap-2">
      <button
        v-for="opcao in [6, 12]"
        :key="opcao"
        type="button"
        class="rounded-lg border px-3.5 py-1.5 text-sm font-semibold cursor-pointer"
        :class="
          meses === opcao
            ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
            : 'border-gray-200 text-gray-600 hover:bg-gray-50'
        "
        @click="meses = opcao"
      >
        {{ opcao }} meses
      </button>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <template v-else-if="serie">
      <!-- A loja começou este mês. Não há UM mês fechado, e nenhuma leitura
           desta tela é dizível — dizer isso é melhor que desenhar um gráfico
           reto no zero e deixar o dono concluir que o sistema está quebrado. -->
      <div
        v-if="disponiveis === 0"
        class="rounded-2xl border border-gray-100 bg-white p-8 text-center shadow-sm"
      >
        <CalendarRange :size="28" class="mx-auto text-gray-300" />
        <p class="mt-3 text-sm font-semibold text-gray-800">
          Ainda não há um mês fechado para comparar
        </p>
        <p class="mx-auto mt-1 max-w-lg text-sm text-gray-500">
          Esta tela fala de meses inteiros: o mês em andamento não entra, porque comparar
          alguns dias com um mês completo acusaria queda todo dia 3. Assim que o mês virar,
          ele aparece aqui — e a cada mês novo uma leitura a mais se abre sozinha.
        </p>
      </div>

      <template v-else>
        <!-- O que dá para dizer do último mês fechado -->
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <TrendingUp :size="15" class="text-emerald-500" /> {{ nomeDoMes(ultimo?.mes) }}
            </p>
            <p class="mt-2 text-xl font-bold text-gray-800">
              {{ formatCurrency(ultimo?.receita ?? 0) }}
            </p>
            <p v-if="rotuloMedia" class="mt-1 text-xs font-semibold" :class="rotuloMedia.cor">
              {{ rotuloMedia.texto }}
            </p>
            <p v-else class="mt-1 text-xs text-gray-400">
              Comparação com a sua média em {{ faltam(PORTAO_MEDIA) }}
              {{ faltam(PORTAO_MEDIA) === 1 ? 'mês' : 'meses' }}
            </p>
          </div>

          <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Variação no mês
            </p>
            <template v-if="variacao !== null">
              <p
                class="mt-2 text-xl font-bold"
                :class="variacao >= 0 ? 'text-emerald-700' : 'text-rose-700'"
              >
                {{ variacao >= 0 ? '+' : '' }}{{ Math.round(variacao * 100) }}%
              </p>
              <p class="mt-1 text-xs text-gray-400">contra {{ nomeDoMes(anterior?.mes) }}</p>
            </template>
            <template v-else>
              <p class="mt-2 text-xl font-bold text-gray-300">—</p>
              <p class="mt-1 text-xs text-gray-400">
                Chega em {{ faltam(PORTAO_COMPARACAO) }}
                {{ faltam(PORTAO_COMPARACAO) === 1 ? 'mês' : 'meses' }}
              </p>
            </template>
          </div>

          <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <Percent :size="15" class="text-gray-400" /> Concentração
            </p>
            <template v-if="concentracao">
              <p class="mt-2 text-xl font-bold text-gray-800">{{ concentracao.fatia }}%</p>
              <p class="mt-1 text-xs" :class="concentracao.fatia >= 80 ? 'text-amber-600 font-semibold' : 'text-gray-400'">
                da receita veio de {{ concentracao.rotulo }}
              </p>
            </template>
            <template v-else>
              <p class="mt-2 text-xl font-bold text-gray-300">—</p>
              <p class="mt-1 text-xs text-gray-400">Você trabalha com uma fonte de receita só</p>
            </template>
          </div>

          <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <Wallet :size="15" class="text-gray-400" /> Prazo de recebimento
            </p>
            <template v-if="prazo !== null">
              <p class="mt-2 text-xl font-bold text-gray-800">{{ prazo }} dias</p>
              <p class="mt-1 text-xs text-gray-400">
                é o que o cliente leva, em média, para pagar
              </p>
            </template>
            <template v-else>
              <!-- Nulo não é zero: zero diria que todo mundo pagou à vista. -->
              <p class="mt-2 text-xl font-bold text-gray-300">—</p>
              <p class="mt-1 text-xs text-gray-400">Nenhuma cobrança a prazo foi quitada no mês</p>
            </template>
          </div>
        </div>

        <section class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <h3 class="text-sm font-bold text-gray-800">De onde veio o dinheiro</h3>
            <p class="text-xs text-gray-400">
              {{ disponiveis }} {{ disponiveis === 1 ? 'mês' : 'meses' }} de histórico ·
              o mês em andamento não entra
            </p>
          </div>
          <div class="mt-4">
            <SerieBarras :meses="historico" />
          </div>
        </section>

        <!-- A PROJEÇÃO — a leitura mais arriscada da tela, e a mais cercada.
             Ela repete a média dos últimos meses e NÃO extrapola a inclinação:
             com seis pontos, uma reta de regressão erra feio e a tela passaria
             a prometer uma data de falência que o dado não sustenta. -->
        <section
          v-if="projecao"
          class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
        >
          <h3 class="flex items-center gap-2 text-sm font-bold text-gray-800">
            <LineChart :size="16" class="text-gray-400" /> Se o ritmo continuar
          </h3>

          <template v-if="projecao.disponivel">
            <div class="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <p class="text-xs text-gray-500">Entra em 12 meses</p>
                <p class="mt-1 text-lg font-bold text-gray-800">
                  {{ formatCurrency(projecao.receita_12_meses) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-gray-500">Sai em 12 meses</p>
                <p class="mt-1 text-lg font-bold text-gray-800">
                  {{ formatCurrency(projecao.despesa_12_meses) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-gray-500">Sobra</p>
                <p
                  class="mt-1 text-lg font-bold"
                  :class="projecao.resultado_12_meses < 0 ? 'text-rose-700' : 'text-emerald-700'"
                >
                  {{ formatCurrency(projecao.resultado_12_meses) }}
                </p>
              </div>
            </div>

            <!-- FAIXA, NUNCA NÚMERO SECO. Número seco vira promessa; e os dois
                 cenários se explicam numa frase, que é o que os torna
                 conferíveis. -->
            <p class="mt-4 rounded-xl bg-gray-50 px-3.5 py-2.5 text-xs text-gray-600">
              Entre <strong>{{ formatCurrency(projecao.piso_12_meses) }}</strong> e
              <strong>{{ formatCurrency(projecao.teto_12_meses) }}</strong> —
              vendendo {{ Math.round(projecao.margem * 100) }}% a menos e gastando
              {{ Math.round(projecao.margem * 100) }}% a mais, ou o contrário.
            </p>

            <p
              v-if="projecao.resultado_mensal < 0"
              class="mt-2 text-xs font-semibold text-rose-600"
            >
              No ritmo dos últimos {{ projecao.base_meses }} meses, cada mês fecha negativo em
              {{ formatCurrency(Math.abs(projecao.resultado_mensal)) }}.
            </p>

            <p class="mt-3 text-xs text-gray-400">
              Conta feita sobre a média dos últimos {{ projecao.base_meses }} meses fechados.
              Ela repete esse ritmo — não adivinha crescimento nem queda.
            </p>
          </template>

          <template v-else>
            <p class="mt-3 text-sm text-gray-500">
              A projeção precisa de 6 meses fechados para existir. Faltam
              <strong>{{ projecao.meses_faltando }}</strong>
              {{ projecao.meses_faltando === 1 ? 'mês' : 'meses' }}.
            </p>
            <p class="mt-1 text-xs text-gray-400">
              Com menos que isso, uma linha de doze meses seria desenhada sobre três pontos —
              e você decidiria em cima dela.
            </p>
          </template>
        </section>

        <!-- O que ainda vai aparecer, com data. É informação, não desculpa: o
             dono precisa saber que a tela cresce sozinha. -->
        <p v-if="disponiveis < 12" class="text-xs text-gray-400">
          A comparação com o mesmo mês do ano passado e a tendência de 12 meses — que é a
          leitura que ignora sazonalidade — precisam de um ano de histórico. Faltam
          {{ 12 - disponiveis }} {{ 12 - disponiveis === 1 ? 'mês' : 'meses' }}.
        </p>
      </template>
    </template>
  </div>
</template>
