<script setup lang="ts">
import { computed } from 'vue';
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
  formatPrintDoc,
} from '@/shared/utils/print.utils';

import PrintCupomHeader from '@/shared/components/print/cupom/PrintCupomHeader.vue';
import PrintCupomSignatures from '@/shared/components/print/cupom/PrintCupomSignatures.vue';
import PrintCupomFooter from '@/shared/components/print/cupom/PrintCupomFooter.vue';

const props = defineProps<{
  sale: SaleRead | OrcamentoRead | null;
  type: 'VENDA' | 'ORCAMENTO';
  paymentMethodResolver?: (id: number) => string;
}>();

const { companyInfo } = useCompanyPrintInfo();

const SEPARATOR = '────────────────────────────';

const isVenda = computed(() => props.type === 'VENDA');

const title = computed(() => isVenda.value ? 'COMPROVANTE DE VENDA' : 'ORÇAMENTO');

const documentId = computed(() => {
  const prefix = isVenda.value ? 'VENDA' : 'ORC';
  const sale = props.sale as SaleRead | null;
  const num = isVenda.value ? (sale?.numero_venda ?? sale?.id ?? 0) : (props.sale?.id ?? 0);
  return `${prefix}: ${String(num).padStart(6, '0')}`;
});

const saleData = computed(() => isVenda.value ? props.sale as SaleRead : null);

const clienteDoc = computed(() => {
  const doc = getClienteDoc(saleData.value?.cliente as any);
  return doc ? formatPrintDoc(doc) : '';
});

const clientePhone = computed(() => {
  return getClientePhone(saleData.value?.cliente as any);
});

const clienteEndereco = computed(() => {
  return getClienteEndereco(saleData.value?.cliente as any);
});

const totalPago = computed(() => {
  if (!saleData.value?.pagamentos) return 0;
  return saleData.value.pagamentos.reduce((acc, pg) => acc + pg.valor, 0);
});
</script>

<template>
  <Teleport to="body">
  <div v-if="sale" class="print-cupom-container hidden print:block">
    <PrintCupomHeader :company="companyInfo" />

    <div class="separator">{{ SEPARATOR }}</div>

    <div class="text-center font-bold my-1">{{ title }}</div>
    <div class="separator">{{ SEPARATOR }}</div>

    <div class="my-1">
      <div><strong>{{ documentId }}</strong></div>
      <div>Data: {{ formatPrintDate(sale.criado_em) }}</div>
    </div>

    <div class="separator">{{ SEPARATOR }}</div>

    <!-- Cliente (apenas venda) -->
    <template v-if="isVenda">
      <div class="section">
        <div class="font-bold mb-0.5">CLIENTE</div>
        <div>{{ getClienteNome(saleData?.cliente as any) }}</div>
        <div v-if="clienteDoc">Doc: {{ clienteDoc }}</div>
        <div v-if="clientePhone">Tel: {{ clientePhone }}</div>
        <div v-if="clienteEndereco">{{ clienteEndereco }}</div>
      </div>

      <div class="separator">{{ SEPARATOR }}</div>
    </template>

    <!-- Itens -->
    <div class="section" v-if="sale.produtos?.length">
      <div class="font-bold mb-0.5">ITENS</div>
      <div
        v-for="item in sale.produtos"
        :key="item.id"
        class="item-row"
      >
        <div>{{ item.nome }}</div>
        <div class="flex justify-between">
          <span>{{ item.quantidade }}x {{ formatCurrency(item.valor_unitario) }}</span>
          <span class="font-bold">{{ formatCurrency(item.total) }}</span>
        </div>
        <div v-if="item.desconto > 0" class="flex justify-between">
          <span>Desc:</span>
          <span>-{{ formatCurrency(item.desconto) }}</span>
        </div>
      </div>
    </div>

    <!-- Pagamentos (apenas venda) -->
    <template v-if="isVenda && saleData?.pagamentos?.length">
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section">
        <div class="font-bold mb-0.5">PAGAMENTOS</div>
        <div
          v-for="pgto in saleData.pagamentos"
          :key="pgto.id"
          class="flex justify-between"
        >
          <span>
            {{ paymentMethodResolver?.(pgto.forma_pagamento_id) }}
            <span v-if="pgto.parcelado && pgto.qtd_parcelas">({{ pgto.qtd_parcelas }}x)</span>
          </span>
          <span>{{ formatCurrency(pgto.valor) }}</span>
        </div>
      </div>
    </template>

    <!-- Totais -->
    <div class="separator">{{ SEPARATOR }}</div>
    <div class="section">
      <div class="flex justify-between">
        <span>Subtotal:</span>
        <span>{{ formatCurrency(sale.subtotal) }}</span>
      </div>
      <div v-if="sale.descontos > 0" class="flex justify-between">
        <span>Desconto:</span>
        <span>-{{ formatCurrency(sale.descontos) }}</span>
      </div>
      <div v-if="sale.entrega > 0" class="flex justify-between">
        <span>Entrega:</span>
        <span>+{{ formatCurrency(sale.entrega) }}</span>
      </div>
      <div v-if="isVenda && (saleData?.acrescimo ?? 0) > 0" class="flex justify-between">
        <span>Juros:</span>
        <span>+{{ formatCurrency(saleData?.acrescimo ?? 0) }}</span>
      </div>
      <div class="flex justify-between font-bold text-sm mt-1">
        <span>TOTAL:</span>
        <span>{{ formatCurrency(sale.total) }}</span>
      </div>
      <template v-if="isVenda">
        <div class="flex justify-between">
          <span>Total Pago:</span>
          <span>{{ formatCurrency(totalPago) }}</span>
        </div>
        <div v-if="saleData && saleData.troco > 0" class="flex justify-between">
          <span>Troco:</span>
          <span>{{ formatCurrency(saleData.troco) }}</span>
        </div>
      </template>
    </div>

    <!-- Observações -->
    <template v-if="sale.observacao">
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section">
        <div class="font-bold mb-0.5">OBSERVACOES</div>
        <div class="whitespace-pre-line">{{ sale.observacao }}</div>
      </div>
    </template>

    <PrintCupomSignatures
      left-label="Vendedor"
      :right-label="isVenda ? 'Assinatura do Cliente' : 'Assinatura'"
      :right-name="isVenda && saleData?.cliente ? getClienteNome(saleData.cliente as any) : undefined"
    />

    <PrintCupomFooter />
  </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-cupom.css';
</style>
