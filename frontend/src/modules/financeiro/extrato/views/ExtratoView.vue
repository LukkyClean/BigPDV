<script setup lang="ts">
/**
 * O Extrato: todo o dinheiro que ANDOU, linha a linha.
 *
 * É o oposto exato do Fluxo de Caixa. Lá a régua olha para frente e só enxerga
 * documento em aberto — conta paga SAI da tela. Aqui nada sai nunca: a tabela
 * por baixo (`movimentacoes_financeiras`) só recebe INSERT, e desfazer um
 * pagamento cria a linha contrária em vez de apagar a original.
 *
 * É por isso que esta é a tela de auditoria: ela conta a história inteira,
 * inclusive a parte que alguém preferiria esquecer. Um extrato que "limpa" o
 * erro não serve para conferir nada.
 */
import { computed, ref } from 'vue';
import { ChevronLeft, ChevronRight, ArrowDownLeft, ArrowUpRight } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { formatData } from '@/shared/utils/date.utils';

import { useOrdemServico } from '@/shared/composables/useOrdemServico';

import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import { useExtratoQuery } from '../../shared/composables/useFinanceiro';

const { range, rotulo, ehMesAtual, anterior, proximo } = usePeriodoMes();
const { usaOrdemServico } = useOrdemServico();

const tipo = ref('');
const origem = ref('');

const filtros = computed(() => ({
  inicio: range.value.inicio,
  fim: range.value.fim,
  tipo: tipo.value,
  origem: origem.value,
}));

const { data: extrato, isLoading } = useExtratoQuery(filtros);

/**
 * Rótulo humano de cada origem.
 *
 * O enum é técnico e viaja no banco; o lojista lê "Pagamento de conta", não
 * "DESPESA". Origem desconhecida cai no próprio código em vez de sumir — se
 * um dia nascer uma origem nova, a linha continua aparecendo no extrato.
 */
const ROTULO_ORIGEM: Record<string, string> = {
  VENDA: 'Venda',
  ORDEM_SERVICO: 'Ordem de serviço',
  ABERTURA: 'Abertura de caixa',
  SANGRIA: 'Sangria',
  SUPRIMENTO: 'Suprimento',
  RECEBIMENTO: 'Recebimento',
  DESPESA: 'Pagamento de conta',
};

/**
 * O rótulo continua existindo para TODA origem, mas a loja sem Ordem de Serviço
 * não vê a opção no filtro: numa adega ou num mercado, "Ordem de serviço" é um
 * filtro que nunca devolve nada.
 *
 * Some da ESCOLHA, não da tradução — se uma linha antiga de OS existir no
 * livro (a loja mudou de segmento, por exemplo), ela continua legível na lista
 * em vez de aparecer como "ORDEM_SERVICO" cru.
 */
const OPCOES_ORIGEM = computed(() =>
  Object.entries(ROTULO_ORIGEM)
    .filter(([valor]) => valor !== 'ORDEM_SERVICO' || usaOrdemServico.value)
    .map(([valor, texto]) => ({ valor, texto })),
);

function rotuloOrigem(valor: string): string {
  return ROTULO_ORIGEM[valor] ?? valor;
}

const temFiltro = computed(() => !!tipo.value || !!origem.value);

function limparFiltros() {
  tipo.value = '';
  origem.value = '';
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Mês, o mesmo seletor das outras telas do módulo -->
    <div class="flex flex-wrap items-center justify-between gap-3">
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

      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="opcao in [
            { valor: '', texto: 'Tudo' },
            { valor: 'ENTRADA', texto: 'Entradas' },
            { valor: 'SAIDA', texto: 'Saídas' },
          ]"
          :key="opcao.valor"
          type="button"
          class="rounded-lg border px-3 py-1.5 text-xs font-semibold cursor-pointer"
          :class="
            tipo === opcao.valor
              ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          "
          @click="tipo = opcao.valor"
        >
          {{ opcao.texto }}
        </button>

        <select
          v-model="origem"
          class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-700 cursor-pointer"
        >
          <option value="">Todas as origens</option>
          <option v-for="o in OPCOES_ORIGEM" :key="o.valor" :value="o.valor">
            {{ o.texto }}
          </option>
        </select>

        <button
          v-if="temFiltro"
          type="button"
          class="text-xs font-medium text-gray-500 underline-offset-2 hover:text-gray-800 hover:underline cursor-pointer"
          @click="limparFiltros"
        >
          Limpar
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <template v-else-if="extrato">
      <!-- Os totais saem do MESMO filtro da lista: um rodapé que não fecha com
           o que está na tela destrói a confiança na tela inteira. -->
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            <ArrowDownLeft :size="15" class="text-emerald-500" /> Entrou
          </p>
          <p class="mt-2 text-xl font-bold text-gray-800">
            {{ formatCurrency(extrato.total_entradas) }}
          </p>
        </div>
        <div class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            <ArrowUpRight :size="15" class="text-rose-500" /> Saiu
          </p>
          <p class="mt-2 text-xl font-bold text-gray-800">
            {{ formatCurrency(extrato.total_saidas) }}
          </p>
        </div>
        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="extrato.saldo < 0 ? 'border-rose-200 bg-rose-50' : 'border-gray-100 bg-white'"
        >
          <p class="text-xs font-semibold uppercase tracking-wide"
             :class="extrato.saldo < 0 ? 'text-rose-600' : 'text-gray-500'">
            Diferença
          </p>
          <p class="mt-2 text-xl font-bold" :class="extrato.saldo < 0 ? 'text-rose-700' : 'text-gray-800'">
            {{ formatCurrency(extrato.saldo) }}
          </p>
          <p class="mt-1 text-xs" :class="extrato.saldo < 0 ? 'text-rose-500' : 'text-gray-400'">
            {{ extrato.total_itens }} movimento(s) no filtro
          </p>
        </div>
      </div>

      <div class="overflow-x-auto rounded-2xl border border-gray-100 bg-white shadow-sm">
        <table class="w-full min-w-[52rem] text-sm">
          <thead>
            <tr class="border-b border-gray-100 text-left text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              <th class="px-5 py-3">Quando</th>
              <th class="px-5 py-3">Origem</th>
              <th class="px-5 py-3">Descrição</th>
              <th class="px-5 py-3">Quem</th>
              <th class="px-5 py-3 text-right">Valor</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="!extrato.itens.length">
              <td colspan="5" class="px-5 py-10 text-center text-sm text-gray-400">
                Nenhum movimento neste filtro. O extrato mostra o dinheiro que já andou —
                conta lançada e ainda não paga aparece no Fluxo de Caixa, não aqui.
              </td>
            </tr>
            <tr v-for="linha in extrato.itens" :key="linha.id" class="hover:bg-gray-50/60">
              <td class="whitespace-nowrap px-5 py-3 text-gray-600">
                {{ formatData(linha.criado_em) }}
              </td>
              <td class="px-5 py-3">
                <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600">
                  {{ rotuloOrigem(linha.origem) }}
                </span>
              </td>
              <td class="px-5 py-3">
                <p class="text-gray-800">
                  {{ linha.documento ?? linha.motivo ?? rotuloOrigem(linha.origem) }}
                </p>
                <p class="text-xs text-gray-400">
                  <template v-if="linha.forma_pagamento_nome">
                    {{ linha.forma_pagamento_nome }}
                  </template>
                  <template v-if="linha.conta_bancaria_nome">
                    · {{ linha.conta_bancaria_nome }}
                  </template>
                  <!-- Dizer que passou pela gaveta importa: é o que separa o
                       dinheiro que o turno tem que fechar do que caiu no banco. -->
                  <template v-if="linha.sessao_caixa_id"> · pelo caixa</template>
                </p>
              </td>
              <td class="px-5 py-3 text-gray-500">{{ linha.funcionario_nome ?? '—' }}</td>
              <td
                class="whitespace-nowrap px-5 py-3 text-right font-semibold tabular-nums"
                :class="linha.tipo === 'ENTRADA' ? 'text-emerald-600' : 'text-rose-600'"
              >
                {{ linha.tipo === 'ENTRADA' ? '+' : '−' }}{{ formatCurrency(linha.valor) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="text-xs text-gray-400">
        Nada é apagado daqui. Um pagamento desfeito não some: ele ganha a linha contrária, e
        as duas ficam — é o que permite auditar o mês depois.
      </p>
    </template>
  </div>
</template>
