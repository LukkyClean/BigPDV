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
import { computed, nextTick, ref } from 'vue';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useRoute } from 'vue-router';
import { ChevronLeft, ChevronRight, ArrowDownLeft, ArrowUpRight, Printer } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { formatData } from '@/shared/utils/date.utils';

import { useOrdemServico } from '@/shared/composables/useOrdemServico';

import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import { useExtratoQuery } from '../../shared/composables/useFinanceiro';
import * as service from '../../shared/services/financeiro.service';
import type { Extrato } from '../../shared/schemas/financeiro.schema';
import { imprimirComPagina } from '@/shared/utils/print.utils';
import { useToast } from '@/shared/composables/useToast';
import ExtratoFinanceiroPrint from '../components/ExtratoFinanceiroPrint.vue';

const toast = useToast();

const route = useRoute();
const { range, rotulo, ehMesAtual, anterior, proximo } = usePeriodoMes(
  route.query.mes as string | undefined,
);
const { usaOrdemServico } = useOrdemServico();

/**
 * Recorte vindo do clique num card da Visão Geral: `?tipo=ENTRADA&mes=2026-09`
 * abre o livro já filtrado no mesmo mês que o dono estava conferindo. Sem
 * query, nada muda -- a tela abre como sempre abriu.
 */
const tipo = ref<string>((route.query.tipo as string) ?? '');
const origem = ref('');

const filtros = computed(() => ({
  inicio: range.value.inicio,
  fim: range.value.fim,
  tipo: tipo.value,
  origem: origem.value,
}));

const { data: extrato, isLoading } = useExtratoQuery(filtros);

// ===========================================================================
// IMPRESSÃO — a primeira do módulo Financeiro
//
// As oito telas dele não imprimiam nada: o dono conferia o mês na tela e
// anotava no papel à mão.
// ===========================================================================

/**
 * Teto do backend. A tela lista 200 por página, mas o papel precisa do período
 * inteiro -- imprimir só a página faria um mês movimentado sair cortado, e um
 * extrato incompleto engana justamente por parecer completo.
 */
const TETO_IMPRESSAO = 500;

const folha = ref<Extrato | null>(null);
const imprimindo = ref(false);

/** O recorte da tela, em português, para ir impresso no papel. */
const rotuloFiltro = computed(() => {
  const partes: string[] = [];
  if (tipo.value) partes.push(tipo.value === 'ENTRADA' ? 'apenas ENTRADAS' : 'apenas SAÍDAS');
  if (origem.value) partes.push(`apenas a origem "${rotuloOrigem(origem.value)}"`);
  return partes.length ? partes.join(' e ') : null;
});

async function imprimir() {
  if (imprimindo.value) return;
  imprimindo.value = true;
  try {
    // Busca própria, e não o cache da tela: aqui o `limit` é outro.
    folha.value = await service.listarExtrato({ ...filtros.value, limit: TETO_IMPRESSAO });
  } catch {
    toast.error('Não foi possível montar o extrato para impressão');
    imprimindo.value = false;
    return;
  }
  await nextTick();

  // Mesmo desmonte da folha de comissão: `afterprint` não dispara em todo
  // cenário (diálogo cancelado de certas formas, impressora virtual), então o
  // timeout evita a folha montada para sempre.
  let fallback: ReturnType<typeof setTimeout>;
  const limpar = () => {
    folha.value = null;
    imprimindo.value = false;
    window.removeEventListener('afterprint', limpar);
    clearTimeout(fallback);
  };
  window.addEventListener('afterprint', limpar);
  fallback = setTimeout(limpar, 60000);
  imprimirComPagina('A4');
}

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

// O BaseSelect fala {value,label}; a lista interna fala {valor,texto}. O item
// vazio entra explicito porque e ele que devolve o filtro para "todas" -- sem
// ele, quem escolhe uma origem nao consegue mais desescolher.
//
// Deriva de OPCOES_ORIGEM, e nao de ROTULO_ORIGEM: e la que mora o filtro por
// segmento, que esconde ORDEM_SERVICO em loja que nao usa OS.
const OPCOES_ORIGEM_SELECT = computed(() => [
  { value: '', label: 'Todas as origens' },
  ...OPCOES_ORIGEM.value.map((o) => ({ value: o.valor, label: o.texto })),
]);

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
  <div class="flex flex-col gap-6 md:gap-8">
    <!-- Cabecalho da secao. Mesmo padrao de Clientes e Produtos:
         PageReview a esquerda, acao principal a direita. -->
    <div class="flex items-center justify-between gap-4">
      <PageReview title="Extrato Financeiro" description="Todo o dinheiro que entrou e saiu, linha a linha" />
    </div>

    <!-- Mês, o mesmo seletor das outras telas do módulo -->
    <div class="flex flex-wrap items-center justify-between gap-3">
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

      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="opcao in [
            { valor: '', texto: 'Tudo' },
            { valor: 'ENTRADA', texto: 'Entradas' },
            { valor: 'SAIDA', texto: 'Saídas' },
          ]"
          :key="opcao.valor"
          type="button"
          class="inline-flex items-center rounded-lg border px-3 py-1.5 text-xs font-semibold min-h-9 cursor-pointer"
          :class="
            tipo === opcao.valor
              ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
              : 'border-zinc-200 text-zinc-600 hover:bg-zinc-50'
          "
          @click="tipo = opcao.valor"
        >
          {{ opcao.texto }}
        </button>

        <div class="w-56">
          <BaseSelect
            v-model="origem"
            :options="OPCOES_ORIGEM_SELECT"
            placeholder="Todas as origens"
          />
        </div>

        <button
          v-if="temFiltro"
          type="button"
          class="text-xs font-medium text-zinc-500 underline-offset-2 hover:text-zinc-800 hover:underline cursor-pointer"
          @click="limparFiltros"
        >
          Limpar
        </button>

        <!-- O papel respeita o recorte da tela, e o diz impresso: uma folha só
             de entradas sem avisar faria o leitor concluir que a loja não teve
             despesa no mês. -->
        <BaseButton
          size="sm"
          class="ml-auto"
          :disabled="imprimindo || !extrato?.itens?.length"
          @click="imprimir"
        >
          <Printer :size="14" class="mr-1.5" />
          {{ imprimindo ? 'Montando…' : 'Imprimir extrato' }}
        </BaseButton>
      </div>
    </div>

    <div v-if="isLoading" class="text-sm text-zinc-500">Carregando…</div>

    <template v-else-if="extrato">
      <!-- Os totais saem do MESMO filtro da lista: um rodapé que não fecha com
           o que está na tela destrói a confiança na tela inteira. -->
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl border border-zinc-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <ArrowDownLeft :size="15" class="text-emerald-500" /> Entrou
          </p>
          <p class="mt-2 text-xl font-bold text-zinc-800">
            {{ formatCurrency(extrato.total_entradas) }}
          </p>
        </div>
        <div class="rounded-2xl border border-zinc-100 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <ArrowUpRight :size="15" class="text-rose-500" /> Saiu
          </p>
          <p class="mt-2 text-xl font-bold text-zinc-800">
            {{ formatCurrency(extrato.total_saidas) }}
          </p>
        </div>
        <div
          class="rounded-2xl border p-5 shadow-sm"
          :class="extrato.saldo < 0 ? 'border-rose-200 bg-rose-50' : 'border-zinc-100 bg-white'"
        >
          <p class="text-xs font-semibold uppercase tracking-wide"
             :class="extrato.saldo < 0 ? 'text-rose-600' : 'text-zinc-500'">
            Diferença
          </p>
          <p class="mt-2 text-xl font-bold" :class="extrato.saldo < 0 ? 'text-rose-700' : 'text-zinc-800'">
            {{ formatCurrency(extrato.saldo) }}
          </p>
          <p class="mt-1 text-xs" :class="extrato.saldo < 0 ? 'text-rose-500' : 'text-zinc-400'">
            {{ extrato.total_itens }} movimento(s) no filtro
          </p>
        </div>
      </div>

      <div class="overflow-x-auto rounded-2xl border border-zinc-100 bg-white shadow-sm">
        <table class="w-full min-w-[52rem] text-sm">
          <thead>
            <tr class="border-b border-zinc-100 text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
              <th class="px-5 py-3">Quando</th>
              <th class="px-5 py-3">Origem</th>
              <th class="px-5 py-3">Descrição</th>
              <th class="px-5 py-3">Quem</th>
              <th class="px-5 py-3 text-right">Valor</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-100">
            <tr v-if="!extrato.itens.length">
              <td colspan="5" class="px-5 py-10 text-center text-sm text-zinc-400">
                Nenhum movimento neste filtro. O extrato mostra o dinheiro que já andou —
                conta lançada e ainda não paga aparece no Fluxo de Caixa, não aqui.
              </td>
            </tr>
            <tr v-for="linha in extrato.itens" :key="linha.id" class="hover:bg-zinc-50/60">
              <td class="whitespace-nowrap px-5 py-3 text-zinc-600">
                {{ formatData(linha.criado_em) }}
              </td>
              <td class="px-5 py-3">
                <span class="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600">
                  {{ rotuloOrigem(linha.origem) }}
                </span>
              </td>
              <td class="px-5 py-3">
                <p class="text-zinc-800">
                  {{ linha.documento ?? linha.motivo ?? rotuloOrigem(linha.origem) }}
                </p>
                <p class="text-xs text-zinc-400">
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
              <td class="px-5 py-3 text-zinc-500">{{ linha.funcionario_nome ?? '—' }}</td>
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

      <p class="text-xs text-zinc-400">
        Nada é apagado daqui. Um pagamento desfeito não some: ele ganha a linha contrária, e
        as duas ficam — é o que permite auditar o mês depois.
      </p>
    </template>

    <ExtratoFinanceiroPrint
      v-if="folha"
      :itens="folha.itens"
      :total-entradas="folha.total_entradas"
      :total-saidas="folha.total_saidas"
      :saldo="folha.saldo"
      :total-itens="folha.total_itens"
      :rotulo-periodo="rotulo"
      :rotulo-filtro="rotuloFiltro"
      :rotulo-origem="rotuloOrigem"
    />
  </div>
</template>
