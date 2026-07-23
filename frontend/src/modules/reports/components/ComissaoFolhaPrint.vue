<script setup lang="ts">
/**
 * @fileoverview Folha de comissão imprimível (A4), no mesmo padrão das impressões
 * de OS/venda. Renderizada só em print (`hidden print:block`) e teleportada para
 * o body para o print-a4.css global isolar só o `.print-container`.
 */
import { computed } from 'vue';

import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { ComissaoItem } from '../schemas/comissao.schema';

const props = defineProps<{
  itens: ComissaoItem[];
  totalPagar: number;
  inicio: string;
  fim: string;
}>();

const { companyInfo } = useCompanyPrintInfo();

function fmtData(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}
const periodo = computed(() => `${fmtData(props.inicio)} a ${fmtData(props.fim)}`);

function pct(bp: number | null): string {
  return bp == null ? '—' : `${(bp / 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
}
</script>

<template>
  <Teleport to="body">
    <div class="print-container hidden print:block bg-white text-black font-sans leading-tight">
      <!-- Cabeçalho da empresa -->
      <header class="flex justify-between items-start gap-4 border border-slate-800 rounded-lg p-4 mb-4">
        <div class="flex items-start gap-3">
          <div class="w-20 h-20 border border-slate-300 rounded-lg flex items-center justify-center shrink-0 overflow-hidden">
            <img v-if="companyInfo.logo" :src="companyInfo.logo" alt="Logo" class="w-full h-full object-contain p-1" />
          </div>
          <div>
            <h1 class="text-lg font-black text-slate-900 uppercase tracking-tight">{{ companyInfo.nome }}</h1>
            <p v-if="companyInfo.razaoSocial" class="text-[10px] uppercase font-bold text-slate-500">{{ companyInfo.razaoSocial }}</p>
            <p v-if="companyInfo.endereco" class="text-xs text-slate-700 mt-1">{{ companyInfo.endereco }}</p>
            <p v-if="companyInfo.cnpj" class="text-xs text-slate-700">
              {{ companyInfo.labelDocumento || 'CNPJ' }}: {{ companyInfo.cnpj }}
            </p>
          </div>
        </div>
        <div class="text-right">
          <div class="bg-slate-900 text-white px-3 py-1.5 rounded-lg">
            <p class="text-[10px] font-bold uppercase tracking-wider">Folha de Comissão</p>
          </div>
          <p class="text-[10px] font-bold text-slate-500 uppercase mt-2">Período</p>
          <p class="text-sm font-bold text-slate-800">{{ periodo }}</p>
        </div>
      </header>

      <!-- Título -->
      <div class="text-center py-2 mb-4 border-y-2 border-slate-200 bg-slate-50">
        <h2 class="text-lg font-black text-slate-800 uppercase tracking-widest">Comissão por Funcionário</h2>
      </div>

      <!-- Tabela -->
      <table class="w-full border-collapse text-xs mb-2">
        <thead>
          <tr class="bg-slate-100 text-slate-700">
            <th class="border border-slate-300 px-2 py-1.5 text-left font-bold uppercase text-[10px]">Funcionário</th>
            <th class="border border-slate-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Vendas</th>
            <th class="border border-slate-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">% V</th>
            <th class="border border-slate-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Serviços</th>
            <th class="border border-slate-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">% S</th>
            <th class="border border-slate-300 px-2 py-1.5 text-right font-bold uppercase text-[10px]">Comissão</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in itens" :key="i.funcionario_id">
            <td class="border border-slate-300 px-2 py-1 text-slate-800">{{ i.nome }}</td>
            <td class="border border-slate-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(i.faturamento_vendas) }}</td>
            <td class="border border-slate-300 px-2 py-1 text-right tabular-nums text-slate-500">{{ pct(i.percentual_venda) }}</td>
            <td class="border border-slate-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(i.faturamento_os) }}</td>
            <td class="border border-slate-300 px-2 py-1 text-right tabular-nums text-slate-500">{{ pct(i.percentual_servico) }}</td>
            <td class="border border-slate-300 px-2 py-1 text-right font-bold tabular-nums">{{ formatCurrency(i.comissao_total) }}</td>
          </tr>
          <tr v-if="itens.length === 0">
            <td colspan="6" class="border border-slate-300 px-2 py-3 text-center text-slate-400">Nenhuma comissão no período.</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="bg-slate-100">
            <td colspan="5" class="border border-slate-300 px-2 py-2 text-right font-black uppercase text-slate-800">Total a pagar</td>
            <td class="border border-slate-300 px-2 py-2 text-right font-black tabular-nums text-slate-900">{{ formatCurrency(totalPagar) }}</td>
          </tr>
        </tfoot>
      </table>

      <p class="text-[10px] text-slate-400 mb-8">
        Base líquida (vendas + OS finalizadas) no período. Percentuais aplicados conforme configuração do cargo/funcionário.
      </p>

      <!-- Assinaturas -->
      <div class="grid grid-cols-2 gap-10 mt-12 text-xs">
        <div class="text-center">
          <div class="border-t border-slate-700 pt-1 text-slate-600">Responsável</div>
        </div>
        <div class="text-center">
          <div class="border-t border-slate-700 pt-1 text-slate-600">Recebido por</div>
        </div>
      </div>

      <PrintFooter />
    </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-a4.css';
</style>
