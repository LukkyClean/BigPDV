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
  pixParaImpressao,
} from '@/shared/utils/print.utils';

import PixQrPrint from '@/shared/components/print/PixQrPrint.vue';
import PrintCupomHeader from '@/shared/components/print/cupom/PrintCupomHeader.vue';
import PrintCupomSignatures from '@/shared/components/print/cupom/PrintCupomSignatures.vue';
import PrintCupomFooter from '@/shared/components/print/cupom/PrintCupomFooter.vue';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
import { useTextosImpressaoOS } from '@/modules/order-service/shared/segmento/textosImpressaoOS';
import { useAtributosImpressaoOS } from '@/modules/order-service/shared/segmento/useAtributosImpressaoOS';
import { formatGarantiaItem } from '@/modules/order-service/shared/utils/formatters';

interface PrintCupomProps {
  orderService: OrderServiceReadDataType | null;
  type: 'ENTRADA' | 'SAIDA' | 'CANCELAMENTO';
}

const props = defineProps<PrintCupomProps>();

const { companyInfo } = useCompanyPrintInfo();
const { labelSingular } = useObjetoLabels();
const { textos, identificadorCupom } = useTextosImpressaoOS();
const { atributos } = useAtributosImpressaoOS();

/** Termos desta via — condensados e sem acento, como o resto do cupom. */
const t = computed(() => textos.value.cupom);

/** Atributos do segmento (oficina: Ano, Chassi, KM). Vazio em informática. */
const atributosObjeto = computed(() =>
  atributos(
    props.orderService?.objeto?.dados_adicionais,
    props.orderService?.dados_adicionais,
  ),
);

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
      if (situacao.value === 'CONDENADO') return `${t.value.objeto.toUpperCase()} CONDENADO`;
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

// Peça embutida no serviço não é listada para o cliente. `!== false` e não
// `=== true`: item antigo vem sem o campo e tem que continuar aparecendo.
const itensVisiveis = computed(() =>
  (props.orderService?.itens ?? []).filter(
    (item) => item.visivel_cliente !== false && item.status_aprovacao !== 'REPROVADO',
  ),
);

const subTotal = computed(() =>
  itensVisiveis.value.reduce((acc, item) => acc + item.valor_total, 0),
);

// Mesma regra da via em papel: com garantia por item, o termo geral não pode
// afirmar que cobre as peças — os dois textos se contradiriam.
const temGarantiaPorItem = computed(() =>
  itensVisiveis.value.some((item) => formatGarantiaItem(item) !== ''),
);

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

/** QR do PIX no papel — só quando há pagamento em PIX e a loja tem chave ativa. */
const pix = computed(() =>
  pixParaImpressao({
    empresa: companyInfo.value,
    pagamentos: props.orderService?.pagamentos?.map((pgto) => ({
      nome: pgto.forma_pagamento?.nome || '',
      valor: pgto.valor,
    })),
    txid: props.orderService?.numero_os ?? undefined,
  }),
);
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
        {{ identificadorCupom }}: {{ orderService.objeto.numero_serie }}
      </div>
      <div v-if="orderService.objeto.cor">
        Cor: {{ orderService.objeto.cor }}
      </div>
      <!-- Atributos do segmento (oficina: Ano, Chassi, KM de entrada). -->
      <div v-for="attr in atributosObjeto" :key="attr.label">
        {{ attr.label }}: {{ attr.valor }}
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

      <template v-if="itensVisiveis.length">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section">
          <div class="font-bold mb-0.5">ITENS/SERVICOS</div>
          <div
            v-for="item in itensVisiveis"
            :key="item.id"
            class="item-row"
          >
            <div>{{ item.nome }}</div>
            <!-- Garantia da peça: só sai quando o mecânico preencheu. -->
            <div v-if="formatGarantiaItem(item)" class="text-[9px]">
              Garantia: {{ formatGarantiaItem(item) }}
            </div>
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

      <!-- PIX: logo depois dos totais, antes da garantia -->
      <template v-if="pix">
        <div class="separator">{{ SEPARATOR }}</div>
        <PixQrPrint :payload="pix.payload" :valor-centavos="pix.valorCentavos" />
      </template>

      <!-- Garantia (só para REPARADO) -->
      <template v-if="!isSemReparo && orderService.garantia">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section text-justify">
          <div class="font-bold mb-0.5">GARANTIA: {{ orderService.garantia }}</div>
          Cobre servicos prestados e pecas substituidas neste documento<template v-if="temGarantiaPorItem">, exceto onde houver garantia indicada na linha do item</template>. Nao cobre {{ t.garantiaExclusoes }}
        </div>
      </template>

      <!-- Entrega sem reparo -->
      <template v-else-if="isSemReparo">
        <div class="separator">{{ SEPARATOR }}</div>
        <div class="section text-justify">
          {{ t.semReparo }}
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
        {{ t.cancelamento }}
      </div>
    </template>

    <!-- ── ENTRADA ── -->
    <template v-else>
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section text-justify">
        {{ t.condicoesEntrada }}
      </div>
      <div class="separator">{{ SEPARATOR }}</div>
      <div class="section text-justify">
        {{ t.prazoRetirada }}
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
