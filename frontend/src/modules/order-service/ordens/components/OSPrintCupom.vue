<script setup lang="ts">
import { computed } from 'vue';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import { formatCurrency } from '@/shared/utils/finance';
import {
  useCompanyPrintInfo,
  getClienteNome,
  getClienteDoc,
  getClientePhone,
  getClienteEndereco,
  getPaymentDisplayName,
  formatPrintDate,
  formatPrintDoc,
  tipoObjetoRelevante,
} from '@/shared/utils/print.utils';

import PrintCupomHeader from '@/shared/components/print/cupom/PrintCupomHeader.vue';
import PrintCupomSignatures from '@/shared/components/print/cupom/PrintCupomSignatures.vue';
import PrintCupomFooter from '@/shared/components/print/cupom/PrintCupomFooter.vue';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';

interface PrintCupomProps {
  orderService: OrderServiceReadDataType | null;
  type: 'ENTRADA' | 'SAIDA' | 'CANCELAMENTO';
}

const props = defineProps<PrintCupomProps>();

const { companyInfo } = useCompanyPrintInfo();
const { labelSingular } = useObjetoLabels();

const SEPARATOR = '────────────────────────────';

const situacao = computed(() => props.orderService?.situacao_equipamento ?? null);

const isSemReparo = computed(() =>
  situacao.value === 'SEM_REPARO' || situacao.value === 'CONDENADO'
);

const title = computed(() => {
  switch (props.type) {
    case 'ENTRADA': return 'COMPROVANTE DE ENTRADA';
    case 'CANCELAMENTO': return 'CANCELAMENTO DE OS';
    case 'SAIDA':
      if (situacao.value === 'SEM_REPARO') return 'ENTREGA SEM REPARO';
      if (situacao.value === 'CONDENADO') return 'OBJETO CONDENADO';
      return 'RECIBO E GARANTIA';
    default: return 'Cupom';
  }
});

const date = computed(() => {
  if (!props.orderService) return '';
  let dateStr: string;
  switch (props.type) {
    case 'SAIDA':
      dateStr = (props.orderService.data_finalizacao as string) || props.orderService.data_criacao;
      break;
    default:
      dateStr = props.orderService.data_criacao;
  }
  return formatPrintDate(dateStr);
});

const clienteDoc = computed(() => {
  const doc = getClienteDoc(props.orderService?.cliente);
  return doc ? formatPrintDoc(doc) : '';
});

const clientePhone = computed(() => {
  return getClientePhone(props.orderService?.cliente);
});

const clienteEndereco = computed(() => {
  return getClienteEndereco(props.orderService?.cliente);
});

// O "tipo" só aparece quando acrescenta info além do rótulo do segmento (em
// oficina ele é o próprio "Veículo" → redundante sob o cabeçalho VEÍCULO).
const mostrarTipoObjeto = computed(() =>
  tipoObjetoRelevante(props.orderService?.objeto?.tipo_equipamento, labelSingular.value),
);

const motivoCancelamento = computed(() => {
  const obs = props.orderService?.observacoes ?? '';
  const match = obs.match(/\[CANCELAMENTO\]\s*([\s\S]+)/);
  return match ? match[1].trim() : 'Motivo nao informado.';
});

const subTotal = computed(() => {
  if (!props.orderService) return 0;
  return props.orderService.itens.reduce((acc, item) => acc + item.valor_total, 0);
});

const adiantamento = computed(() => props.orderService?.valor_entrada ?? 0);

const adiantamentoUtilizado = computed(() => {
  const entrada = adiantamento.value;
  const total = props.orderService?.valor_total ?? 0;
  return Math.min(entrada, total);
});

const paymentTotal = computed(() => {
  if (!props.orderService?.pagamentos) return 0;
  return props.orderService.pagamentos.reduce((acc, pay) => acc + pay.valor, 0);
});

const totalRecebido = computed(() => adiantamentoUtilizado.value + paymentTotal.value);
</script>

<template>
  <Teleport to="body">
  <div v-if="orderService" class="print-cupom-container hidden print:block">
    <PrintCupomHeader :company="companyInfo" />

    <div class="separator">{{ SEPARATOR }}</div>

    <div class="text-center font-bold my-1">{{ title }}</div>
    <div class="separator">{{ SEPARATOR }}</div>

    <div class="flex justify-between my-1">
      <span>OS: <strong>{{ orderService.numero_os }}</strong></span>
    </div>
    <div>Data: {{ date }}</div>

    <div class="separator">{{ SEPARATOR }}</div>

    <div class="section">
      <div class="font-bold mb-0.5">CLIENTE</div>
      <div>{{ getClienteNome(orderService.cliente) }}</div>
      <div v-if="clienteDoc">Doc: {{ clienteDoc }}</div>
      <div v-if="clientePhone">Tel: {{ clientePhone }}</div>
      <div v-if="clienteEndereco">{{ clienteEndereco }}</div>
    </div>

    <div class="separator">{{ SEPARATOR }}</div>

    <div class="section">
      <div class="font-bold mb-0.5">{{ labelSingular.toUpperCase() }}</div>
      <div v-if="mostrarTipoObjeto || (situacao && type === 'SAIDA')" class="flex items-center gap-1">
        <span v-if="mostrarTipoObjeto">{{ orderService.objeto.tipo_equipamento }}</span>
        <span v-if="situacao && type === 'SAIDA'" class="text-[9px] font-bold uppercase">
          ({{ situacao === 'REPARADO' ? 'Reparado' : situacao === 'SEM_REPARO' ? 'Sem Reparo' : 'Condenado' }})
        </span>
      </div>
      <div v-if="orderService.objeto.marca">
        Marca: {{ orderService.objeto.marca }}
      </div>
      <div v-if="orderService.objeto.modelo">
        Modelo: {{ orderService.objeto.modelo }}
      </div>
      <div v-if="orderService.objeto.numero_serie">
        N/S: {{ orderService.objeto.numero_serie }}
      </div>
      <div v-if="orderService.objeto.cor">
        Cor: {{ orderService.objeto.cor }}
      </div>
    </div>

    <div class="separator">{{ SEPARATOR }}</div>

    <div class="section">
      <div class="font-bold mb-0.5">DEFEITO RELATADO</div>
      <div>{{ orderService.defeito_relatado }}</div>
    </div>

    <template v-if="orderService.observacoes">
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section">
        <div class="font-bold mb-0.5">OBSERVACOES</div>
        <div class="whitespace-pre-line">{{ orderService.observacoes }}</div>
      </div>
    </template>

    <!-- ── SAÍDA ── -->
    <template v-if="type === 'SAIDA'">
      <template v-if="orderService.diagnostico || orderService.solucao">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section">
          <div class="font-bold mb-0.5">LAUDO TECNICO</div>
          <div v-if="orderService.diagnostico">
            Diag: {{ orderService.diagnostico }}
          </div>
          <div v-if="orderService.solucao">
            Solucao: {{ orderService.solucao }}
          </div>
        </div>
      </template>

      <template v-if="orderService.itens?.length">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section">
          <div class="font-bold mb-0.5">ITENS/SERVICOS</div>
          <div
            v-for="item in orderService.itens"
            :key="item.id"
            class="item-row"
          >
            <div>{{ item.nome }}</div>
            <div class="flex justify-between">
              <span>{{ item.quantidade }}x {{ formatCurrency(item.valor_unitario) }}</span>
              <span class="font-bold">{{ formatCurrency(item.valor_total) }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Adiantamento -->
      <template v-if="adiantamento > 0">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section">
          <div class="font-bold mb-0.5">ADIANTAMENTO (ENTRADA)</div>
          <div class="flex justify-between">
            <span>Recebido na entrada:</span>
            <span class="font-bold">{{ formatCurrency(adiantamento) }}</span>
          </div>
        </div>
      </template>

      <!-- Pagamentos no fechamento -->
      <template v-if="orderService.pagamentos?.length">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section">
          <div class="font-bold mb-0.5">PAGAMENTOS</div>
          <div
            v-for="pgto in orderService.pagamentos"
            :key="pgto.id"
            class="flex justify-between"
          >
            <span>
              {{ getPaymentDisplayName(pgto.forma_pagamento?.nome || 'Pagamento') }}
              <span v-if="pgto.parcelas > 1">({{ pgto.parcelas }}x)</span>
            </span>
            <span>{{ formatCurrency(pgto.valor) }}</span>
          </div>
        </div>
      </template>

      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section">
        <div class="flex justify-between">
          <span>Subtotal:</span>
          <span>{{ formatCurrency(subTotal) }}</span>
        </div>
        <div v-if="(orderService.desconto ?? 0) > 0" class="flex justify-between">
          <span>Desconto:</span>
          <span>-{{ formatCurrency(orderService.desconto ?? 0) }}</span>
        </div>
        <div v-if="(orderService.taxa_entrega ?? 0) > 0" class="flex justify-between">
          <span>Deslocamento:</span>
          <span>+{{ formatCurrency(orderService.taxa_entrega ?? 0) }}</span>
        </div>
        <div v-if="(orderService.acrescimo ?? 0) > 0" class="flex justify-between">
          <span>Juros:</span>
          <span>+{{ formatCurrency(orderService.acrescimo ?? 0) }}</span>
        </div>
        <div v-if="adiantamento > 0" class="flex justify-between">
          <span>Adiantamento:</span>
          <span>-{{ formatCurrency(adiantamentoUtilizado) }}</span>
        </div>
        <div class="flex justify-between font-bold text-sm mt-1">
          <span>TOTAL PAGO:</span>
          <span>{{ formatCurrency(totalRecebido) }}</span>
        </div>
        <template v-if="(orderService.acrescimo ?? 0) > 0">
          <div class="separator">{{ SEPARATOR }}</div>
          <div class="font-bold text-[9px] uppercase mb-0.5">Devolucao</div>
          <div class="flex justify-between text-[9px]">
            <span>Servico (dinheiro):</span>
            <span>{{ formatCurrency(paymentTotal - (orderService.acrescimo ?? 0)) }}</span>
          </div>
          <div class="flex justify-between text-[9px]">
            <span>Estorno cartao:</span>
            <span>{{ formatCurrency(paymentTotal) }}</span>
          </div>
        </template>
      </div>

      <!-- Garantia (só para REPARADO) -->
      <template v-if="!isSemReparo && orderService.garantia">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section text-justify">
          <div class="font-bold mb-0.5">GARANTIA: {{ orderService.garantia }}</div>
          Cobre servicos prestados e pecas substituidas neste documento. Nao cobre mau uso, liquidos, quedas ou intervencao de terceiros.
        </div>
      </template>

      <!-- Entrega sem reparo -->
      <template v-else-if="isSemReparo">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section text-justify">
          Objeto devolvido sem reparo.
          Sem garantia aplicavel a esta OS.
        </div>
      </template>
    </template>

    <!-- ── CANCELAMENTO ── -->
    <template v-else-if="type === 'CANCELAMENTO'">
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section">
        <div class="font-bold mb-0.5">MOTIVO DO CANCELAMENTO</div>
        <div>{{ motivoCancelamento }}</div>
      </div>
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section text-justify">
        A OS acima foi cancelada nesta data.
        Objeto devolvido ao cliente sem
        reparos ou com reparos parciais,
        isentando a assistencia de garantias
        sobre servicos nao concluidos.
      </div>
    </template>

    <!-- ── ENTRADA ── -->
    <template v-else>
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section text-justify">
        O cliente declara estar ciente que a
        empresa nao se responsabiliza por
        perda de dados nem por chips/cartoes
        deixados no aparelho. Autorizo a
        analise tecnica do objeto.
      </div>
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section text-justify">
        PRAZO DE RETIRADA: Objetos nao
        retirados em 90 dias apos aviso de
        conclusao serao considerados
        abandonados, conforme Art. 1.275
        do Codigo Civil Brasileiro.
      </div>
    </template>

    <PrintCupomSignatures
      left-label="Tecnico Responsavel"
      right-label="Assinatura do Cliente"
      :right-name="orderService.cliente ? getClienteNome(orderService.cliente) : undefined"
    />

    <PrintCupomFooter />
  </div>
  </Teleport>
</template>

<style>
@import '@/shared/components/print/styles/print-cupom.css';
</style>
