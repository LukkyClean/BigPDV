<script setup lang="ts">
/**
 * @fileoverview O livro do dinheiro em papel (A4). Mesmo molde da folha de
 * comissão e do extrato de serviços: `hidden print:block` + Teleport para o
 * body, para o print-a4.css global isolar só o `.print-container`.
 *
 * PRIMEIRA IMPRESSÃO DO MÓDULO FINANCEIRO. As oito telas dele não imprimiam
 * nada — o dono conferia o mês na tela e anotava no papel à mão.
 *
 * UMA FOLHA, DUAS PARTES, porque os três usos reais são o mesmo papel:
 *   resumo no topo   → mandar pro contador, arquivar o mês, prestar contas
 *   detalhe abaixo   → sentar com o extrato do banco ao lado e ir riscando
 *
 * O SALDO ACUMULADO é DO PERÍODO, não da conta bancária. Ele começa em zero no
 * primeiro movimento da folha e serve para achar ONDE a conferência divergiu.
 * Chamá-lo de "saldo" sem o rótulo faria o dono comparar com o saldo do banco e
 * achar que o sistema está errado — a loja pode ter dinheiro de antes do
 * período, e o Fluxo de Caixa é quem responde isso.
 */
import { computed } from 'vue';

import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { ExtratoLinha } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{
  itens: ExtratoLinha[];
  totalEntradas: number;
  totalSaidas: number;
  saldo: number;
  totalItens: number;
  rotuloPeriodo: string;
  /** O recorte que está na tela. Vai impresso: papel sem filtro declarado engana. */
  rotuloFiltro: string | null;
  rotuloOrigem: (valor: string) => string;
}>();

const { companyInfo } = useCompanyPrintInfo();

function dataHora(iso: string): { dia: string; hora: string } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { dia: '—', hora: '' };
  return {
    dia: d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
    hora: d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
  };
}

/** Quanto entrou e quanto saiu em cada origem — o "de onde veio" do resumo. */
const porOrigem = computed(() => {
  const mapa = new Map<string, { entrou: number; saiu: number; qtd: number }>();
  for (const l of props.itens) {
    const atual = mapa.get(l.origem) ?? { entrou: 0, saiu: 0, qtd: 0 };
    if (l.tipo === 'ENTRADA') atual.entrou += l.valor;
    else atual.saiu += l.valor;
    atual.qtd += 1;
    mapa.set(l.origem, atual);
  }
  return [...mapa.entries()]
    .map(([origem, v]) => ({ origem, ...v }))
    .sort((a, b) => b.entrou - b.saiu - (a.entrou - a.saiu));
});

/**
 * Os itens em ordem CRONOLÓGICA, com o acumulado. A tela lista do mais recente
 * para o mais antigo (é o que se quer olhar); no papel de conferência a ordem
 * tem de ser a do banco, senão o acumulado não significa nada.
 */
const linhas = computed(() => {
  const ordenadas = [...props.itens].sort(
    (a, b) => new Date(a.criado_em).getTime() - new Date(b.criado_em).getTime(),
  );
  let acumulado = 0;
  return ordenadas.map((l) => {
    acumulado += l.tipo === 'ENTRADA' ? l.valor : -l.valor;
    return { ...l, acumulado };
  });
});

/**
 * O backend devolve no máximo 500 linhas. Num mês acima disso a folha sai
 * incompleta, e ela PRECISA dizer -- extrato cortado engana justamente por
 * parecer inteiro. Os totais do topo continuam corretos: eles vêm do filtro
 * inteiro no servidor, não da soma das linhas impressas.
 */
const cortado = computed(() => props.totalItens > props.itens.length);

const emitidoEm = new Date().toLocaleString('pt-BR', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});
</script>

<template>
  <Teleport to="body">
    <div class="print-container extrato-folha hidden print:block bg-white text-black font-sans leading-tight">
      <header class="flex justify-between items-start gap-4 border border-neutral-800 rounded-lg p-4 mb-4">
        <div class="flex items-start gap-3">
          <div class="w-20 h-20 border border-neutral-300 rounded-lg flex items-center justify-center shrink-0 overflow-hidden">
            <img v-if="companyInfo.logo" :src="companyInfo.logo" alt="Logo" class="w-full h-full object-contain p-1" />
          </div>
          <div>
            <h1 class="text-lg font-black text-neutral-900 uppercase tracking-tight">{{ companyInfo.nome }}</h1>
            <p v-if="companyInfo.razaoSocial" class="text-[10px] uppercase font-bold text-neutral-600">{{ companyInfo.razaoSocial }}</p>
            <p v-if="companyInfo.endereco" class="text-xs text-neutral-800 mt-1">{{ companyInfo.endereco }}</p>
            <p v-if="companyInfo.cnpj" class="text-xs text-neutral-800">
              {{ companyInfo.labelDocumento || 'CNPJ' }}: {{ companyInfo.cnpj }}
            </p>
          </div>
        </div>
        <div class="text-right">
          <div class="bg-neutral-900 text-white px-3 py-1.5 rounded-lg">
            <p class="text-[10px] font-bold uppercase tracking-wider">Movimento de Caixa</p>
          </div>
          <p class="text-[10px] font-bold text-neutral-600 uppercase mt-2">Período</p>
          <p class="text-sm font-bold text-neutral-900">{{ rotuloPeriodo }}</p>
        </div>
      </header>

      <!-- O RECORTE VAI IMPRESSO. Uma folha que mostra só as entradas sem dizer
           isso faz o leitor concluir que a loja não teve despesa no mês. -->
      <p
        v-if="rotuloFiltro"
        class="mb-3 border border-neutral-400 rounded px-3 py-1.5 text-[11px] text-neutral-800"
      >
        <strong>Atenção:</strong> esta folha mostra {{ rotuloFiltro }}. Não é o movimento
        completo do período.
      </p>

      <p
        v-if="cortado"
        class="mb-3 border border-neutral-400 rounded px-3 py-1.5 text-[11px] text-neutral-800"
      >
        <strong>Folha incompleta:</strong> o período tem {{ totalItens }} lançamentos e esta
        folha lista os {{ itens.length }} primeiros. Os totais acima continuam sendo do
        período inteiro. Reduza o período para imprimir tudo.
      </p>

      <!-- ===== RESUMO ===== -->
      <div class="grid grid-cols-3 gap-3 mb-4">
        <div class="border border-neutral-300 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Entrou</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(totalEntradas) }}</p>
        </div>
        <div class="border border-neutral-300 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Saiu</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(totalSaidas) }}</p>
        </div>
        <div class="border-2 border-neutral-800 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-600">Diferença</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(saldo) }}</p>
        </div>
      </div>

      <div v-if="porOrigem.length" class="mb-4">
        <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-1">
          De onde veio e para onde foi
        </p>
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-neutral-100">
              <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Origem</th>
              <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Mov.</th>
              <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Entrou</th>
              <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Saiu</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in porOrigem" :key="o.origem">
              <td class="border border-neutral-300 px-2 py-1">{{ rotuloOrigem(o.origem) }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ o.qtd }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">
                {{ o.entrou ? formatCurrency(o.entrou) : '—' }}
              </td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">
                {{ o.saiu ? formatCurrency(o.saiu) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ===== DETALHE ===== -->
      <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-1">
        Movimento linha a linha &middot; {{ totalItens }} lançamento(s)
      </p>
      <table class="w-full border-collapse text-xs tabela-detalhe">
        <thead>
          <!-- REPETE EM TODA FOLHA. Um extrato de três páginas vira três papéis
               soltos; sem esta linha, a folha 2 não diz de que loja nem de que
               mês ela é. Vive no `thead` porque é o único jeito de repetir
               conteúdo por página no Chrome — ele não suporta as margens
               nomeadas do `@page`. -->
          <tr class="hidden print:table-row">
            <th
              colspan="5"
              class="border-x border-t border-neutral-300 px-2 pt-1 pb-0 text-left text-[9px] font-normal text-neutral-500"
            >
              {{ companyInfo.nome }} &middot; Movimento de caixa &middot; {{ rotuloPeriodo }}
            </th>
          </tr>
          <tr class="bg-neutral-100">
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Data</th>
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Origem</th>
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Descrição</th>
            <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Valor</th>
            <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Acum.</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in linhas" :key="l.id" class="break-inside-avoid">
            <td class="border border-neutral-300 px-2 py-1 whitespace-nowrap tabular-nums">
              {{ dataHora(l.criado_em).dia }}
              <span class="text-neutral-500">{{ dataHora(l.criado_em).hora }}</span>
            </td>
            <td class="border border-neutral-300 px-2 py-1 whitespace-nowrap">{{ rotuloOrigem(l.origem) }}</td>
            <td class="border border-neutral-300 px-2 py-1">
              {{ l.documento || l.motivo || '—' }}
              <span v-if="l.forma_pagamento_nome" class="text-neutral-500">
                &middot; {{ l.forma_pagamento_nome }}
              </span>
            </td>
            <td class="border border-neutral-300 px-2 py-1 text-right font-bold tabular-nums whitespace-nowrap">
              {{ l.tipo === 'ENTRADA' ? '+' : '−' }}{{ formatCurrency(l.valor) }}
            </td>
            <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums whitespace-nowrap">
              {{ formatCurrency(l.acumulado) }}
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="bg-neutral-100">
            <td colspan="3" class="border border-neutral-400 px-2 py-1.5 text-right font-bold uppercase text-[10px]">
              Diferença do período
            </td>
            <td colspan="2" class="border border-neutral-400 px-2 py-1.5 text-right text-sm font-black tabular-nums">
              {{ formatCurrency(saldo) }}
            </td>
          </tr>
        </tfoot>
      </table>

      <p class="mt-2 text-[9px] text-neutral-500">
        "Acum." é o acumulado DESTE período, começando do zero no primeiro lançamento — serve
        para localizar onde a conferência divergiu, e não é o saldo da conta bancária.
        Emitido em {{ emitidoEm }}.
      </p>

      <PrintFooter />
    </div>
  </Teleport>
</template>

<style>
/*
 * REGRAS DA FOLHA DE VÁRIAS PÁGINAS — escopadas em `.extrato-folha` de
 * propósito.
 *
 * O print-a4.css é global e vale para as vias de OS e de venda que já rodam nas
 * três lojas em produção. Mexer nele para resolver um caso do Financeiro é o
 * tipo de mudança que quebra impressão que ninguém estava olhando.
 */
@media print {
  /* O cabeçalho da tabela se repete no topo de CADA folha. É o padrão do
     navegador, mas declarar explicitamente evita depender dele: sem isso, a
     página 2 vem com uma tabela de números sem nome de coluna. */
  .extrato-folha .tabela-detalhe thead {
    display: table-header-group;
  }

  /* O rodapé NÃO se repete. `tfoot` também é table-footer-group por padrão em
     parte dos motores, e aí o total do período apareceria no pé de todas as
     folhas como se fosse o total daquela página. */
  .extrato-folha .tabela-detalhe tfoot {
    display: table-row-group;
  }

  /* O resumo do topo fica inteiro na primeira folha: quebrá-lo ao meio separa
     "Entrou" de "Saiu" em páginas diferentes. */
  .extrato-folha > .grid,
  .extrato-folha header {
    page-break-inside: avoid;
  }
}
</style>
