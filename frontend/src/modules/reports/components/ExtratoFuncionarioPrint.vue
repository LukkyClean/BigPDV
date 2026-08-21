<script setup lang="ts">
/**
 * @fileoverview Extrato de serviços imprimível (A4), no mesmo padrão da folha de
 * comissão. Renderizado só em print (`hidden print:block`) e teleportado para o
 * body para o print-a4.css global isolar só o `.print-container`.
 *
 * É o papel que o dono entrega em mãos, então ele responde sozinho às perguntas
 * que o funcionário vai fazer: o que eu fiz, em qual OS, de quem era o carro,
 * quanto somou. Sem o extrato na frente, essas respostas viram discussão.
 */
import { computed } from 'vue';

import { useCompanyPrintInfo } from '@/shared/utils/print.utils';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { ExtratoServicoItem } from '../schemas/extratoFuncionario.schema';

const props = defineProps<{
  funcionario: string;
  itens: ExtratoServicoItem[];
  qtdOs: number;
  qtdServicos: number;
  valorTotal: number;
  inicio: string;
  fim: string;
}>();

const { companyInfo } = useCompanyPrintInfo();

function fmtData(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}
const periodo = computed(() => `${fmtData(props.inicio)} a ${fmtData(props.fim)}`);

/** "12/08" — no corpo da tabela o ano é ruído: ele já está no período do topo. */
function diaMes(iso: string): string {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

/**
 * Quantidade sem casa decimal quando é inteira.
 *
 * Serviço costuma ser 1, mas a coluna é `Float` — serigrafia trabalha com
 * quantidade fracionária. "1,00" numa folha de oficina é ruído; "2,5" numa de
 * serigrafia é a informação.
 */
function fmtQtd(q: number): string {
  return Number.isInteger(q) ? String(q) : q.toLocaleString('pt-BR', { maximumFractionDigits: 3 });
}
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
            <p class="text-[10px] font-bold uppercase tracking-wider">Extrato de Serviços</p>
          </div>
          <p class="text-[10px] font-bold text-neutral-600 uppercase mt-2">Período</p>
          <p class="text-sm font-bold text-neutral-900">{{ periodo }}</p>
        </div>
      </header>

      <!-- Quem -->
      <div class="text-center py-2 mb-4 border-y-2 border-neutral-200 bg-neutral-50">
        <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-500">Funcionário</p>
        <h2 class="text-lg font-black text-neutral-900 uppercase tracking-widest">{{ funcionario }}</h2>
      </div>

      <table class="w-full border-collapse text-xs">
        <thead>
          <tr class="bg-neutral-100">
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Data</th>
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">OS</th>
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Objeto / Cliente</th>
            <th class="border border-neutral-300 px-2 py-1 text-left font-bold uppercase text-[10px]">Serviço</th>
            <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Qtd</th>
            <th class="border border-neutral-300 px-2 py-1 text-right font-bold uppercase text-[10px]">Valor</th>
          </tr>
        </thead>
        <tbody>
          <!--
            A OS e o objeto se repetem em cada linha, em vez de célula vazia.
            O papel é conferido item a item, e uma célula em branco obriga quem lê
            a subir para saber de qual OS aquilo é.
          -->
          <tr v-for="(i, idx) in itens" :key="`${i.numero_os}-${idx}`">
            <td class="border border-neutral-300 px-2 py-1 tabular-nums">{{ diaMes(i.data_finalizacao) }}</td>
            <td class="border border-neutral-300 px-2 py-1 font-medium">{{ i.numero_os }}</td>
            <td class="border border-neutral-300 px-2 py-1">
              <span v-if="i.objeto">{{ i.objeto }}</span>
              <span v-if="i.objeto && i.cliente"> · </span>
              <span v-if="i.cliente">{{ i.cliente }}</span>
              <span v-if="!i.objeto && !i.cliente" class="text-neutral-400">—</span>
            </td>
            <td class="border border-neutral-300 px-2 py-1">{{ i.servico }}</td>
            <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ fmtQtd(i.quantidade) }}</td>
            <td class="border border-neutral-300 px-2 py-1 text-right tabular-nums">{{ formatCurrency(i.valor_total) }}</td>
          </tr>

          <tr v-if="!itens.length">
            <td colspan="6" class="border border-neutral-300 px-2 py-4 text-center text-neutral-500">
              Nenhum serviço finalizado neste período.
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="bg-neutral-100 font-bold">
            <td colspan="4" class="border border-neutral-300 px-2 py-1.5 text-right uppercase text-[11px]">
              {{ qtdServicos }} serviço(s) em {{ qtdOs }} OS
            </td>
            <td class="border border-neutral-300 px-2 py-1.5 text-right uppercase text-[11px]">Total</td>
            <td class="border border-neutral-300 px-2 py-1.5 text-right tabular-nums text-sm">
              {{ formatCurrency(valorTotal) }}
            </td>
          </tr>
        </tfoot>
      </table>

      <!--
        A ressalva existe porque o papel vai para a mão de quem recebe comissão:
        sem ela, "total" é lido como "o que eu ganho". Não é — é o que a loja
        cobrou pelo trabalho, e a comissão tem folha própria.
      -->
      <p class="mt-3 text-[10px] text-neutral-600 leading-snug">
        Valores referentes ao que foi cobrado pelos serviços executados. Peças aplicadas não
        entram neste extrato. Este documento não é demonstrativo de comissão.
      </p>

      <PrintFooter />
    </div>
  </Teleport>
</template>
