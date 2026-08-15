<script setup lang="ts">
/**
 * @fileoverview Relatório financeiro imprimível (A4), no mesmo padrão da folha de
 * comissão. Renderizado só em print (`hidden print:block`) e teleportado para o
 * body para o print-a4.css global isolar só o `.print-container`.
 *
 * Espelha o que está na tela, inclusive as ressalvas: os blocos de juros e de
 * lucro aparecem sob as mesmas condições, e o aviso de custo não apurado vem
 * junto. Um relatório impresso que omitisse a ressalva viraria um número bonito e
 * errado circulando fora do sistema, onde ninguém pode conferir.
 */
import { computed } from 'vue';

import { useCompanyPrintInfo, getPaymentDisplayName } from '@/shared/utils/print.utils';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { RelatorioFaturamento } from '../schemas/faturamento.schema';

const props = defineProps<{ dados: RelatorioFaturamento }>();

const { companyInfo } = useCompanyPrintInfo();

function fmtData(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

const periodo = computed(() => `${fmtData(props.dados.inicio)} a ${fmtData(props.dados.fim)}`);

const jurosTotal = computed(
  () => (props.dados.juros_repassado ?? 0) + (props.dados.juros_absorvido ?? 0),
);

const liquido = computed(
  () => props.dados.faturamento_liquido ?? props.dados.faturamento_total,
);

// Mesma regra da tela: sem custo apurado, "Lucro = Faturamento" não informa nada.
const temCusto = computed(
  () => (props.dados.cmv ?? 0) > 0 || (props.dados.saidas_sem_custo ?? 0) > 0,
);

/** Só dias com movimento — dia zerado ocupa linha e não diz nada. */
const diasComMovimento = computed(() => props.dados.por_dia.filter((d) => d.total_geral > 0));
</script>

<template>
  <Teleport to="body">
    <div class="print-container hidden print:block bg-white text-black font-sans leading-tight">
      <!-- Cabeçalho da empresa -->
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
            <p class="text-[10px] font-bold uppercase tracking-wider">Relatório Financeiro</p>
          </div>
          <p class="text-[10px] font-bold text-neutral-600 uppercase mt-2">Período</p>
          <p class="text-sm font-bold text-neutral-900">{{ periodo }}</p>
        </div>
      </header>

      <!-- Resumo -->
      <div class="text-center py-2 mb-4 border-y-2 border-neutral-200 bg-neutral-50">
        <h2 class="text-lg font-black text-neutral-900 uppercase tracking-widest">Resumo do Período</h2>
      </div>

      <div class="grid grid-cols-4 gap-2 mb-5">
        <div class="border border-neutral-300 rounded-lg p-2.5 text-center">
          <p class="text-[9px] font-bold uppercase text-neutral-600 tracking-wider">Faturamento</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(liquido) }}</p>
          <p class="text-[9px] text-neutral-600 mt-0.5">
            {{ dados.qtd_vendas }} vendas &middot; {{ dados.qtd_os }} OS
          </p>
        </div>
        <div class="border border-neutral-300 rounded-lg p-2.5 text-center">
          <p class="text-[9px] font-bold uppercase text-neutral-600 tracking-wider">Ticket médio</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(dados.ticket_medio) }}</p>
        </div>
        <div class="border border-neutral-300 rounded-lg p-2.5 text-center">
          <p class="text-[9px] font-bold uppercase text-neutral-600 tracking-wider">Vendas</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(dados.faturamento_vendas) }}</p>
          <p class="text-[9px] text-neutral-600 mt-0.5">{{ dados.qtd_vendas }} finalizadas</p>
        </div>
        <div class="border border-neutral-300 rounded-lg p-2.5 text-center">
          <p class="text-[9px] font-bold uppercase text-neutral-600 tracking-wider">Serviços (OS)</p>
          <p class="text-base font-black text-neutral-900 tabular-nums mt-1">{{ formatCurrency(dados.faturamento_os) }}</p>
          <p class="text-[9px] text-neutral-600 mt-0.5">{{ dados.qtd_os }} finalizadas</p>
        </div>
      </div>

      <!-- Juros de cartão: só quando existe -->
      <div v-if="jurosTotal > 0" class="mb-5">
        <h3 class="text-xs font-black uppercase text-neutral-800 tracking-wider border-b border-neutral-300 pb-1 mb-2">
          Juros de cartão
        </h3>
        <table class="w-full border-collapse text-xs">
          <tbody>
            <tr>
              <td class="border border-neutral-300 px-2 py-1 text-neutral-700">Faturamento bruto</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(dados.faturamento_total) }}</td>
            </tr>
            <tr v-if="(dados.juros_repassado ?? 0) > 0">
              <td class="border border-neutral-300 px-2 py-1 text-neutral-700">
                (−) Juros repassado ao cliente
                <span class="text-[9px] text-neutral-600">· cobrado a mais, fica com a operadora</span>
              </td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">− {{ formatCurrency(dados.juros_repassado ?? 0) }}</td>
            </tr>
            <tr v-if="(dados.juros_absorvido ?? 0) > 0">
              <td class="border border-neutral-300 px-2 py-1 text-neutral-700">
                (−) Juros absorvido pela loja
                <span class="text-[9px] text-neutral-600">· o cliente não pagou, a loja bancou</span>
              </td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">− {{ formatCurrency(dados.juros_absorvido ?? 0) }}</td>
            </tr>
            <tr class="bg-neutral-100">
              <td class="border border-neutral-300 px-2 py-1.5 font-black uppercase text-neutral-900">Faturamento líquido</td>
              <td class="border border-neutral-300 px-2 py-1.5 text-right font-black tabular-nums">{{ formatCurrency(liquido) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Lucro: só quando há custo apurado ou aviso a dar -->
      <div v-if="temCusto" class="mb-5">
        <h3 class="text-xs font-black uppercase text-neutral-800 tracking-wider border-b border-neutral-300 pb-1 mb-2">
          Lucro no período
        </h3>
        <table class="w-full border-collapse text-xs">
          <tbody>
            <tr>
              <td class="border border-neutral-300 px-2 py-1 text-neutral-700">Faturamento líquido</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(liquido) }}</td>
            </tr>
            <tr>
              <td class="border border-neutral-300 px-2 py-1 text-neutral-700">
                (−) Custo das peças vendidas
                <span class="text-[9px] text-neutral-600">· o que você pagou por elas</span>
              </td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">− {{ formatCurrency(dados.cmv ?? 0) }}</td>
            </tr>
            <tr class="bg-neutral-100">
              <td class="border border-neutral-300 px-2 py-1.5 font-black uppercase text-neutral-900">
                Lucro bruto
                <span class="text-[9px] font-normal normal-case text-neutral-600">· não desconta despesa fixa</span>
              </td>
              <td class="border border-neutral-300 px-2 py-1.5 text-right font-black tabular-nums">
                {{ formatCurrency(dados.lucro_bruto ?? 0) }}
                <span class="text-[10px] font-semibold text-neutral-600">
                  ({{ (dados.margem_percentual ?? 0).toFixed(1) }}%)
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <p v-if="(dados.saidas_sem_custo ?? 0) > 0" class="mt-2 text-[10px] text-neutral-800 border border-neutral-400 rounded p-2">
          <strong>Atenção:</strong> {{ dados.saidas_sem_custo }} movimentação(ões) deste período são
          anteriores ao registro de custo e entraram como zero.
          <strong>O lucro acima está maior do que o real</strong> — ele fica exato conforme as peças
          forem entrando com o valor pago.
        </p>
      </div>

      <!-- Formas de pagamento -->
      <div v-if="dados.formas_pagamento.length" class="mb-5">
        <h3 class="text-xs font-black uppercase text-neutral-800 tracking-wider border-b border-neutral-300 pb-1 mb-2">
          Formas de pagamento
        </h3>
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-neutral-100 text-neutral-800">
              <th class="border border-neutral-300 px-2 py-1.5 text-left font-bold uppercase text-[10px]">Forma</th>
              <th class="border border-neutral-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in dados.formas_pagamento" :key="f.nome">
              <td class="border border-neutral-300 px-2 py-1 text-neutral-900">{{ getPaymentDisplayName(f.nome) }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(f.valor_total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Detalhamento por dia -->
      <div class="mb-6">
        <h3 class="text-xs font-black uppercase text-neutral-800 tracking-wider border-b border-neutral-300 pb-1 mb-2">
          Detalhamento por dia
        </h3>
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-neutral-100 text-neutral-800">
              <th class="border border-neutral-300 px-2 py-1.5 text-left font-bold uppercase text-[10px]">Dia</th>
              <th class="border border-neutral-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Vendas</th>
              <th class="border border-neutral-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">OS</th>
              <th class="border border-neutral-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in diasComMovimento" :key="d.dia">
              <td class="border border-neutral-300 px-2 py-1 text-neutral-900">{{ fmtData(d.dia) }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(d.total_vendas) }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(d.total_os) }}</td>
              <td class="border border-neutral-300 px-2 py-1 text-right font-bold tabular-nums">{{ formatCurrency(d.total_geral) }}</td>
            </tr>
            <tr v-if="diasComMovimento.length === 0">
              <td colspan="4" class="border border-neutral-300 px-2 py-3 text-center text-neutral-600">
                Nenhum movimento no período.
              </td>
            </tr>
          </tbody>
          <tfoot v-if="diasComMovimento.length">
            <tr class="bg-neutral-100">
              <td class="border border-neutral-300 px-2 py-1.5 font-black uppercase text-neutral-900">Total bruto</td>
              <td class="border border-neutral-300 px-2 py-1.5 text-right font-bold tabular-nums">{{ formatCurrency(dados.faturamento_vendas) }}</td>
              <td class="border border-neutral-300 px-2 py-1.5 text-right font-bold tabular-nums">{{ formatCurrency(dados.faturamento_os) }}</td>
              <td class="border border-neutral-300 px-2 py-1.5 text-right font-black tabular-nums">{{ formatCurrency(dados.faturamento_total) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <PrintFooter />
    </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-a4.css';
</style>
