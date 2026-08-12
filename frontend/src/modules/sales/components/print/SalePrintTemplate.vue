<script setup lang="ts">
import { computed } from 'vue';
import { User, CreditCard, ShoppingBag } from 'lucide-vue-next';
import type { SaleRead } from '../../schemas/sale.schema';
import type { OrcamentoRead } from '../../schemas/orcamento.schema';
import { formatCurrency } from '@/shared/utils/finance';
import {
  useCompanyPrintInfo,
  getClienteNome,
  getClienteDoc,
  getClientePhone,
  getClienteEndereco,
  formatPrintDate,
  formatPrintPhone,
  formatPrintDoc,
  pixParaImpressao,
} from '@/shared/utils/print.utils';

import PixQrPrint from '@/shared/components/print/PixQrPrint.vue';
import PrintCompanyHeader from '@/shared/components/print/a4/PrintCompanyHeader.vue';
import PrintSignatures from '@/shared/components/print/a4/PrintSignatures.vue';
import PrintFooter from '@/shared/components/print/a4/PrintFooter.vue';
import { usePerfilComprovante } from '@/shared/composables/usePerfilComprovante';

const props = defineProps<{
  sale: SaleRead | OrcamentoRead | null;
  type: 'VENDA' | 'ORCAMENTO';
  paymentMethodResolver?: (id: number) => string;
}>();

const { companyInfo } = useCompanyPrintInfo();

// Densidade do layout. Venda e orçamento seguem o mesmo documento comercial.
const { classeDensidade } = usePerfilComprovante('venda_recibo');

const isVenda = computed(() => props.type === 'VENDA');

const title = computed(() => isVenda.value ? 'COMPROVANTE DE VENDA' : 'ORÇAMENTO');

const documentLabel = computed(() => isVenda.value ? 'Nº da Venda' : 'Nº do Orçamento');

const documentNumber = computed(() => {
  const sale = props.sale as SaleRead | null;
  const num = isVenda.value ? (sale?.numero_venda ?? sale?.id ?? 0) : (props.sale?.id ?? 0);
  return String(num).padStart(6, '0');
});

const saleData = computed(() => isVenda.value ? props.sale as SaleRead : null);

const totalPago = computed(() => {
  if (!saleData.value?.pagamentos) return 0;
  return saleData.value.pagamentos.reduce((acc, pg) => acc + pg.valor, 0);
});

/** QR do PIX no papel — só quando há pagamento em PIX e a loja tem chave ativa. */
const pix = computed(() =>
  pixParaImpressao({
    empresa: companyInfo.value,
    pagamentos: saleData.value?.pagamentos?.map((pgto) => ({
      nome: props.paymentMethodResolver?.(pgto.forma_pagamento_id) ?? '',
      valor: pgto.valor,
    })),
  }),
);
</script>

<template>
  <Teleport to="body">
  <div
    v-if="sale"
    class="print-container hidden print:block bg-white text-black font-sans leading-tight"
    :class="classeDensidade"
  >
    <PrintCompanyHeader
      :company="companyInfo"
      :document-label="documentLabel"
      :document-number="documentNumber"
      date-label="Data"
      :date-value="formatPrintDate(sale.criado_em)"
    />

    <div class="text-center py-2 mb-4 border-y-2 border-neutral-200 bg-neutral-50">
      <h2 class="text-lg font-black text-neutral-900 uppercase tracking-widest">{{ title }}</h2>
    </div>

    <!-- Dados do Cliente (apenas venda) -->
    <div v-if="isVenda" class="mb-4">
      <div class="border border-neutral-300 rounded-lg overflow-hidden">
        <div class="bg-neutral-100 px-3 py-1.5 border-b border-neutral-200 flex items-center gap-2">
          <User :size="14" class="text-neutral-600" />
          <h3 class="text-xs font-bold uppercase text-neutral-800">Dados do Cliente</h3>
        </div>
        <div class="p-3 text-xs space-y-1.5">
          <p><span class="font-bold text-neutral-700">Nome:</span> {{ saleData?.cliente ? getClienteNome(saleData.cliente as any) : 'Consumidor Final' }}</p>
          <div class="flex gap-4">
            <p v-if="getClienteDoc(saleData?.cliente as any)"><span class="font-bold text-neutral-700">CPF/CNPJ:</span> {{ formatPrintDoc(getClienteDoc(saleData?.cliente as any)) }}</p>
            <p v-if="getClientePhone(saleData?.cliente as any)"><span class="font-bold text-neutral-700">Telefone:</span> {{ formatPrintPhone(getClientePhone(saleData?.cliente as any)) }}</p>
          </div>
          <p v-if="getClienteEndereco(saleData?.cliente as any)"><span class="font-bold text-neutral-700">Endereço:</span> {{ getClienteEndereco(saleData?.cliente as any) }}</p>
          <p v-if="saleData?.cliente?.id"><span class="font-bold text-neutral-700">Cód. Cliente:</span> #{{ saleData.cliente.id }}</p>
        </div>
      </div>
    </div>

    <!-- Tabela de Itens -->
    <div class="mb-4" v-if="sale.produtos?.length">
      <div class="flex items-center gap-2 mb-2">
        <ShoppingBag :size="14" class="text-neutral-600" />
        <h3 class="text-xs font-bold uppercase text-neutral-800">{{ isVenda ? 'Itens da Venda' : 'Itens do Orçamento' }}</h3>
      </div>
      <table class="w-full text-xs text-left">
        <thead>
          <tr class="border-b-2 border-neutral-800">
            <th class="py-2 pl-2 text-neutral-700 uppercase font-bold w-[40%]">Produto</th>
            <th class="py-2 text-center text-neutral-700 uppercase font-bold w-[12%]">SKU</th>
            <th class="py-2 text-center text-neutral-700 uppercase font-bold w-[8%]">Qtd</th>
            <th class="py-2 text-right text-neutral-700 uppercase font-bold w-[13%]">Unit.</th>
            <th class="py-2 text-right text-neutral-700 uppercase font-bold w-[13%]">Desc.</th>
            <th class="py-2 pr-2 text-right text-neutral-700 uppercase font-bold w-[14%]">Total</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-200">
          <tr v-for="item in sale.produtos" :key="item.id">
            <td class="py-2 pl-2 text-neutral-900">{{ item.nome }}</td>
            <td class="py-2 text-center text-neutral-600">{{ item.sku || '-' }}</td>
            <td class="py-2 text-center text-neutral-700">{{ item.quantidade }}</td>
            <td class="py-2 text-right text-neutral-700">{{ formatCurrency(item.valor_unitario) }}</td>
            <td class="py-2 text-right text-neutral-700">{{ item.desconto > 0 ? `- ${formatCurrency(item.desconto)}` : '-' }}</td>
            <td class="py-2 pr-2 text-right font-bold text-neutral-900">{{ formatCurrency(item.total) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagamentos (apenas venda) -->
    <div class="grid grid-cols-2 gap-6 mb-4" v-if="isVenda">
        <div>
          <p class="text-[10px] font-bold text-neutral-600 uppercase mb-2 border-b border-neutral-200 pb-1">Detalhes do Pagamento</p>
          <div v-if="saleData?.pagamentos?.length" class="space-y-1.5">
            <div v-for="pgto in saleData.pagamentos" :key="pgto.id" class="flex justify-between items-center text-xs bg-neutral-50 p-1.5 rounded border border-neutral-100">
              <div class="flex items-center gap-2">
                <CreditCard :size="12" class="text-neutral-600" />
                <span class="font-semibold text-neutral-800">
                  {{ paymentMethodResolver?.(pgto.forma_pagamento_id) }}
                  <span v-if="pgto.parcelado && pgto.qtd_parcelas" class="text-[10px] text-neutral-600 font-normal">({{ pgto.qtd_parcelas }}x)</span>
                </span>
              </div>
              <span class="font-bold text-neutral-900">{{ formatCurrency(pgto.valor) }}</span>
            </div>
          </div>
          <div v-else class="text-xs text-neutral-600 italic py-2">Nenhum pagamento registrado.</div>
        </div>

        <!-- Resumo financeiro -->
        <div class="space-y-1 text-right">
          <!-- O cabeçalho não é enfeite: sem ele esta coluna começava no topo da
               linha do grid e o "Subtotal" alinhava com o TÍTULO da coluna de
               pagamentos, não com o conteúdo dela. -->
          <p class="text-[10px] font-bold text-neutral-600 uppercase mb-2 border-b border-neutral-200 pb-1 text-left">Resumo Financeiro</p>
          <div class="flex justify-between text-xs text-neutral-600">
            <span>Subtotal:</span>
            <span>{{ formatCurrency(sale.subtotal) }}</span>
          </div>
          <div v-if="sale.descontos > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Desconto:</span>
            <span>- {{ formatCurrency(sale.descontos) }}</span>
          </div>
          <div v-if="sale.entrega > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Entrega:</span>
            <span>+ {{ formatCurrency(sale.entrega) }}</span>
          </div>
          <div v-if="(saleData?.acrescimo ?? 0) > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Juros:</span>
            <span>+ {{ formatCurrency(saleData?.acrescimo ?? 0) }}</span>
          </div>
          <div class="border-t border-neutral-800 my-1 pt-1 flex justify-between items-end">
            <span class="text-sm font-bold text-neutral-900 uppercase">Total:</span>
            <span class="text-xl font-black text-neutral-900 leading-none">{{ formatCurrency(sale.total) }}</span>
          </div>
          <div class="flex justify-between text-xs text-neutral-600">
            <span>Total Pago:</span>
            <span>{{ formatCurrency(totalPago) }}</span>
          </div>
          <div v-if="saleData && saleData.troco > 0" class="flex justify-between text-xs text-neutral-600">
            <span>Troco:</span>
            <span>{{ formatCurrency(saleData.troco) }}</span>
          </div>
        </div>
      </div>

    <!-- Totais (apenas orçamento) -->
    <div v-if="!isVenda" class="mb-4">
      <div class="space-y-1 text-right">
        <div class="flex justify-between text-xs text-neutral-600">
          <span>Subtotal:</span>
          <span>{{ formatCurrency(sale.subtotal) }}</span>
        </div>
        <div v-if="sale.descontos > 0" class="flex justify-between text-xs text-neutral-600">
          <span>Desconto:</span>
          <span>- {{ formatCurrency(sale.descontos) }}</span>
        </div>
        <div v-if="sale.entrega > 0" class="flex justify-between text-xs text-neutral-600">
          <span>Entrega:</span>
          <span>+ {{ formatCurrency(sale.entrega) }}</span>
        </div>
        <div class="border-t border-neutral-800 my-1 pt-1 flex justify-between items-end">
          <span class="text-sm font-bold text-neutral-900 uppercase">Total:</span>
          <span class="text-xl font-black text-neutral-900 leading-none">{{ formatCurrency(sale.total) }}</span>
        </div>
      </div>
    </div>

    <!-- PIX: o QR fecha o documento financeiro, logo abaixo dos totais -->
    <div v-if="pix" class="mb-4 border border-neutral-300 rounded-lg p-3 inline-block">
      <PixQrPrint :payload="pix.payload" :valor-centavos="pix.valorCentavos" lado="30mm" />
    </div>

    <!-- Observações -->
    <div v-if="sale.observacao" class="mb-4 border border-dashed border-neutral-300 rounded-lg p-3">
      <p class="text-[10px] font-bold text-neutral-600 uppercase mb-1">Observações</p>
      <p class="text-xs text-neutral-800 whitespace-pre-line">{{ sale.observacao }}</p>
    </div>

    <PrintSignatures
      left-label="Vendedor"
      :right-label="isVenda ? 'Assinatura do Cliente' : 'Assinatura'"
      :right-name="isVenda && saleData?.cliente ? getClienteNome(saleData.cliente as any) : undefined"
    />

    <PrintFooter />
  </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-a4.css';
</style>
