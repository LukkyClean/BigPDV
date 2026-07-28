<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import { storeToRefs } from 'pinia';
import {
  X,
  Trash2,
  CreditCard,
  Wallet,
  QrCode,
  Banknote,
  FileText,
  RotateCcw,
  Percent,
} from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import {
  getPaymentDisplayName,
  inferPaymentType,
  inferPermiteParcelamento,
} from '@/shared/utils/print.utils';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';

import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useFinishSaleModal } from '../../composables/flows/useFinishSaleModal';
import { useFinishSaleMutation } from '../../composables/mutates/useFinishSaleMutation';
import { usePaymentMethodsQuery } from '../../composables/queries/usePaymentMethodsQuery';
import {
  useJurosPagamento,
  JUROS_RESPONSAVEL_OPTIONS,
} from '@/shared/composables/useJurosPagamento';

import type { SaleRead } from '../../schemas/sale.schema';
import type { CardFlag } from '../../schemas/paymentSale.schema';
import type { PaymentFormReadDataType } from '@/shared/schemas/payments/payment.schema';

const props = defineProps<{
  sale: SaleRead | undefined;
}>();

const emit = defineEmits<{
  finalized: [sale: SaleRead];
}>();

const saleTotal = computed(() => props.sale?.total ?? 0);

const {
  payments,
  finishModalIsOpen,
  closeFinishModal,
  addPayment,
  removePayment,
  totalPago,
  acrescimo,
  jurosLoja,
  troco,
  restante,
  canFinish,
} = useFinishSaleModal(saleTotal);

// Juros do pagamento que está sendo montado no sub-modal.
const {
  taxaInput: jurosTaxaInput,
  responsavel: jurosResponsavel,
  temJuros: jurosAtivo,
  lojaAbsorve: jurosLojaAbsorve,
  calcular: calcularJuros,
  normalizar: normalizarJuros,
  reset: resetJuros,
} = useJurosPagamento();

const finishMutation = useFinishSaleMutation();
const { formasPagamento } = usePaymentMethodsQuery();
const { permitirParcelamento, parcelasMaximas } = storeToRefs(useConfiguracoesStore());

// Estado local do sub-modal de detalhes do pagamento
const showPaymentDetails = ref(false);
const currentPaymentMethod = ref<PaymentFormReadDataType | null>(null);
const paymentValueReais = ref(0);
const moneyInputRef = ref();
const confirmacao = ref(false);

const paymentDetails = ref<{
  parcelas: number;
  bandeira: CardFlag | '';
  vencimento?: string;
  banco_destino?: string;
  codigo_transacao?: string;
}>({
  parcelas: 1,
  bandeira: '',
  vencimento: new Date().toISOString().split('T')[0],
  banco_destino: '',
  codigo_transacao: '',
});

// Computed values
const activePaymentMethods = computed(() =>
  formasPagamento.value.filter((fp) => fp.ativo),
);

const displaySubtotal = computed(() => formatCurrency(props.sale?.subtotal ?? 0));
const displayDiscount = computed(() => formatCurrency(props.sale?.descontos ?? 0));
const displayDelivery = computed(() => formatCurrency(props.sale?.entrega ?? 0));
const totalComAcrescimo = computed(() => saleTotal.value + acrescimo.value);
const displayTotal = computed(() => formatCurrency(totalComAcrescimo.value));
const displayTotalPago = computed(() => formatCurrency(totalPago.value));
const displayTroco = computed(() => formatCurrency(troco.value));

const canFinishWithConfirmation = computed(() => canFinish.value && confirmacao.value);

const paymentBaseCentavos = computed(() => Math.round(paymentValueReais.value * 100));
/** Juros do pagamento em edição. Só existe para cartão. */
const jurosDoPagamentoAtual = computed(() =>
  currentPaymentMethod.value && getMethodTipo(currentPaymentMethod.value).includes('CARTAO')
    ? calcularJuros(paymentBaseCentavos.value)
    : 0,
);
/** O que o cliente efetivamente paga: só sobe se o juros for repassado. */
const valorCobradoDoCliente = computed(
  () => paymentBaseCentavos.value + (jurosLojaAbsorve.value ? 0 : jurosDoPagamentoAtual.value),
);

// Parcelas com o valor de cada parcela já refletindo o que o cliente vai pagar.
const parcelasOptions = computed(() => {
  const options = [{ value: 1, label: 'À vista' }];
  const totalParcelar = valorCobradoDoCliente.value;
  const max = Math.max(2, parcelasMaximas.value || 12);
  for (let i = 2; i <= max; i++) {
    options.push({ value: i, label: `${i}x de ${formatCurrency(Math.round(totalParcelar / i))}` });
  }
  return options;
});

// Helpers de pagamento
function getMethodTipo(method: PaymentFormReadDataType): string {
  return method.tipo ?? inferPaymentType(method.nome);
}

function getMethodPermiteParcelamento(method: PaymentFormReadDataType): boolean {
  return method.permite_parcelamento ?? inferPermiteParcelamento(getMethodTipo(method));
}

// Exibe parcelamento quando a config permite e a forma aceita (cartão ou boleto).
function displayParcelasFor(method: PaymentFormReadDataType): boolean {
  if (!permitirParcelamento.value) return false;
  return getMethodPermiteParcelamento(method) || getMethodTipo(method) === 'BOLETO';
}

function getPaymentIcon(tipo: string) {
  switch (tipo) {
    case 'DINHEIRO':       return Banknote;
    case 'PIX':            return QrCode;
    case 'CARTAO_CREDITO': return CreditCard;
    case 'CARTAO_DEBITO':  return Wallet;
    case 'BOLETO':         return FileText;
    default:               return Banknote;
  }
}

function getPaymentIconById(id: number) {
  const method = formasPagamento.value.find((f) => f.id === id);
  return getPaymentIcon(method ? getMethodTipo(method) : '');
}

function getPaymentMethodName(formaId: number): string {
  const method = formasPagamento.value.find((fp) => fp.id === formaId);
  return getPaymentDisplayName(method?.nome ?? 'Desconhecido');
}

function getValorPorMetodo(formaId: number): number {
  return payments.value
    .filter(p => p.forma_pagamento_id === formaId)
    .reduce((sum, p) => sum + p.valor, 0);
}

function clearPayments() {
  while (payments.value.length > 0) {
    removePayment(0);
  }
}

// Ações de pagamento
function handleAddPaymentClick(method: PaymentFormReadDataType) {
  currentPaymentMethod.value = method;
  paymentValueReais.value = restante.value / 100;
  paymentDetails.value = {
    parcelas: 1,
    bandeira: '',
    vencimento: new Date().toISOString().split('T')[0],
    banco_destino: '',
    codigo_transacao: '',
  };
  resetJuros();
  showPaymentDetails.value = true;
  nextTick(() => {
    if (moneyInputRef.value?.inputRef) {
      moneyInputRef.value.inputRef.select();
    }
  });
}

function confirmAddPayment() {
  const method = currentPaymentMethod.value;
  if (!method || paymentValueReais.value <= 0) return;

  const tipo = getMethodTipo(method);
  const baseValor = paymentBaseCentavos.value;
  const jurosAmount = jurosDoPagamentoAtual.value;
  const responsavel = jurosResponsavel.value;

  const podeParcelar = displayParcelasFor(method);
  const parcelado = podeParcelar && paymentDetails.value.parcelas > 1;

  let detalhes: Record<string, unknown> | undefined;
  if (tipo.includes('TRANSFERENCIA') && (paymentDetails.value.banco_destino || paymentDetails.value.codigo_transacao)) {
    detalhes = {
      banco_destino: paymentDetails.value.banco_destino || undefined,
      codigo_transacao: paymentDetails.value.codigo_transacao || undefined,
    };
  }

  addPayment({
    forma_pagamento_id: method.id,
    parcelado,
    qtd_parcelas: parcelado ? paymentDetails.value.parcelas : null,
    // Quando a loja absorve, o cliente paga só a base — o juros fica registrado
    // à parte, como custo, e não infla o total da venda.
    valor: responsavel === 'LOJA' ? baseValor : baseValor + jurosAmount,
    juros_valor: jurosAmount,
    juros_responsavel: responsavel,
    bandeira_cartao: tipo.includes('CARTAO') ? (paymentDetails.value.bandeira || undefined) : undefined,
    vencimento: tipo === 'BOLETO' ? paymentDetails.value.vencimento : undefined,
    detalhes,
  });

  showPaymentDetails.value = false;
  currentPaymentMethod.value = null;
}

function handleRemovePayment(index: number) {
  removePayment(index);
}

function handleCloseFinishModal() {
  confirmacao.value = false;
  closeFinishModal();
}

function handleFinish() {
  if (!props.sale || !canFinishWithConfirmation.value) return;

  finishMutation.mutate(
    { saleId: props.sale.id, payments: payments.value, acrescimo: acrescimo.value },
    {
      onSuccess: (finishedSale) => {
        confirmacao.value = false;
        closeFinishModal();
        emit('finalized', finishedSale);
      },
    },
  );
}
</script>

<template>
  <BaseModal :is-open="finishModalIsOpen" title="Finalizar Venda" size="3xl" overflow="hidden">
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
        <h2 class="text-xl font-bold text-zinc-800">Finalizar Venda</h2>
        <button
          type="button"
          class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
          @click="handleCloseFinishModal"
        >
          <X :size="20" />
        </button>
      </div>
    </template>

    <div class="flex flex-col gap-4 h-[calc(90vh-140px)]">

      <!-- Linha principal: esq (formas + pagamentos) + dir (resumo) -->
      <div class="grid grid-cols-2 gap-4 flex-1 min-h-0">

        <!-- Coluna esquerda: formas de pagamento + lista -->
        <div class="flex flex-col gap-2 min-h-0">

          <!-- Formas de pagamento (compact 3-col) -->
          <div class="shrink-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1.5">Selecionar Forma de Pagamento</p>
            <div data-payment-grid class="grid grid-cols-3 gap-1.5">
              <button
                v-for="method in activePaymentMethods"
                :key="method.id"
                type="button"
                :disabled="restante <= 0"
                class="flex flex-col items-center justify-center p-1.5 rounded-lg border-2 transition-all gap-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                :class="getValorPorMetodo(method.id) > 0
                  ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
                  : 'border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-500 hover:border-zinc-300'"
                @click="handleAddPaymentClick(method)"
              >
                <component :is="getPaymentIcon(getMethodTipo(method))" :size="14" />
                <span class="text-[9px] font-medium text-center leading-tight">
                  {{ getPaymentDisplayName(method.nome) }}
                </span>
                <span
                  class="text-[9px] font-bold tabular-nums"
                  :class="getValorPorMetodo(method.id) > 0 ? 'text-brand-primary' : 'text-zinc-300'"
                >
                  {{ getValorPorMetodo(method.id) > 0 ? formatCurrency(getValorPorMetodo(method.id)) : '—' }}
                </span>
              </button>
            </div>
          </div>

          <!-- Lista de pagamentos -->
          <div class="border border-zinc-200 rounded-xl overflow-hidden flex flex-col flex-1 min-h-0">
            <div class="bg-zinc-100 px-4 py-2 border-b border-zinc-200 flex items-center justify-between shrink-0">
              <p class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Pagamentos</p>
              <div class="flex items-center gap-2">
                <span class="text-[10px] text-zinc-400">{{ payments.length }} item(s)</span>
                <button
                  type="button"
                  :disabled="payments.length === 0"
                  class="flex items-center gap-1 text-[10px] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  :class="payments.length > 0 ? 'text-red-400 hover:text-red-600 cursor-pointer' : 'text-zinc-400'"
                  @click="clearPayments"
                >
                  <RotateCcw :size="11" />
                  Zerar
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-3 space-y-2">
              <div v-if="payments.length === 0" class="h-full flex items-center justify-center py-8">
                <p class="text-xs text-zinc-400">Nenhum pagamento registrado</p>
              </div>

              <div
                v-for="(payment, idx) in payments"
                :key="idx"
                class="flex items-center justify-between p-2.5 bg-white border border-zinc-100 rounded-lg shadow-sm"
              >
                <div class="flex items-center gap-2.5">
                  <div class="p-1.5 bg-zinc-50 rounded-lg text-brand-primary">
                    <component :is="getPaymentIconById(payment.forma_pagamento_id)" :size="14" />
                  </div>
                  <div>
                    <p class="text-xs font-semibold text-zinc-700">
                      {{ getPaymentMethodName(payment.forma_pagamento_id) }}
                      <span v-if="payment.parcelado" class="font-normal text-zinc-400"> · {{ payment.qtd_parcelas }}x</span>
                      <span v-if="payment.bandeira_cartao" class="font-normal text-zinc-400"> · {{ payment.bandeira_cartao }}</span>
                    </p>
                    <template v-if="(payment.juros_valor ?? 0) > 0 && payment.juros_responsavel !== 'LOJA'">
                      <p class="text-[10px] text-zinc-400">
                        Venda: {{ formatCurrency(payment.valor - (payment.juros_valor ?? 0)) }}
                        <span class="text-amber-500"> + Juros: {{ formatCurrency(payment.juros_valor ?? 0) }}</span>
                        = {{ formatCurrency(payment.valor) }}
                      </p>
                    </template>
                    <template v-else-if="(payment.juros_valor ?? 0) > 0">
                      <p class="text-[10px] text-zinc-400">
                        {{ formatCurrency(payment.valor) }}
                        <span class="text-rose-500"> · loja absorve {{ formatCurrency(payment.juros_valor ?? 0) }}</span>
                      </p>
                    </template>
                    <template v-else>
                      <p class="text-[10px] text-zinc-400">{{ formatCurrency(payment.valor) }}</p>
                    </template>
                  </div>
                </div>
                <button
                  type="button"
                  class="text-zinc-300 hover:text-red-500 p-1.5 cursor-pointer transition-colors"
                  @click="handleRemovePayment(idx)"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
          </div>

        </div><!-- fim coluna esquerda -->

        <!-- Coluna direita: Resumo financeiro -->
        <div class="border border-zinc-200 rounded-xl overflow-hidden flex flex-col">
          <div class="bg-zinc-100 px-4 py-2 border-b border-zinc-200">
            <p class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Resumo Financeiro</p>
          </div>
          <div class="p-4 space-y-2.5 overflow-y-auto flex-1 no-scrollbar">

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Subtotal dos itens</span>
              <span class="text-base font-semibold text-zinc-800">{{ displaySubtotal }}</span>
            </div>

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Desconto</span>
              <span
                class="text-base"
                :class="(sale?.descontos ?? 0) > 0 ? 'font-semibold text-emerald-600' : 'font-medium text-zinc-400'"
              >
                {{ (sale?.descontos ?? 0) > 0 ? `- ${displayDiscount}` : '—' }}
              </span>
            </div>

            <div v-if="(sale?.entrega ?? 0) > 0" class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Entrega</span>
              <span class="text-base font-medium text-zinc-700">{{ displayDelivery }}</span>
            </div>

            <div v-if="acrescimo > 0" class="flex justify-between items-center">
              <span class="text-xs text-amber-600 flex items-center gap-1">
                <Percent :size="12" /> Juros repassado
              </span>
              <span class="text-base font-medium text-amber-600">+ {{ formatCurrency(acrescimo) }}</span>
            </div>

            <div v-if="jurosLoja > 0" class="flex justify-between items-center">
              <span class="text-xs text-rose-600 flex items-center gap-1">
                <Percent :size="12" /> Juros absorvido pela loja
              </span>
              <span class="text-base font-medium text-rose-600">{{ formatCurrency(jurosLoja) }}</span>
            </div>

            <!-- Divisor -->
            <div class="border-t border-zinc-200 pt-2.5 space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-bold text-zinc-700">Total a pagar</span>
                <span class="text-xl font-bold text-brand-primary">{{ displayTotal }}</span>
              </div>

              <div
                class="flex justify-between items-center font-semibold"
                :class="totalPago >= totalComAcrescimo ? 'text-emerald-600' : 'text-zinc-400'"
              >
                <span class="text-sm">Total recebido</span>
                <span class="text-lg">{{ displayTotalPago }}</span>
              </div>

              <!-- Breakdown de devolução (só exibe quando há juros, de qualquer origem) -->
              <div
                v-if="(acrescimo > 0 || jurosLoja > 0) && totalPago > 0"
                class="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 space-y-1"
              >
                <p class="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">Em caso de devolução</p>
                <div v-if="acrescimo > 0" class="flex justify-between items-center text-xs text-zinc-600">
                  <span>Venda (sem juros)</span>
                  <span class="font-semibold">{{ formatCurrency(totalPago - acrescimo) }}</span>
                </div>
                <p v-if="acrescimo > 0" class="text-[10px] text-amber-600">
                  Juros pagos à operadora pelo cliente: {{ formatCurrency(acrescimo) }}
                </p>
                <p v-if="jurosLoja > 0" class="text-[10px] text-rose-600">
                  A loja não recupera {{ formatCurrency(jurosLoja) }} de juros absorvidos.
                </p>
              </div>

              <div v-if="restante > 0" class="flex justify-between items-center font-bold text-red-500">
                <span class="text-sm">Faltam</span>
                <span class="text-lg">{{ formatCurrency(restante) }}</span>
              </div>

              <div v-if="troco > 0" class="flex justify-between items-center font-bold text-amber-500">
                <span class="text-sm">Troco</span>
                <span class="text-lg">{{ displayTroco }}</span>
              </div>
            </div>
          </div>
        </div>

      </div><!-- fim grid -->

      <!-- Confirmação + botões (dentro do body) -->
      <div class="flex items-center gap-4 pt-3 border-t border-zinc-200 shrink-0">
        <BaseCheckbox
          v-model="confirmacao"
          :label="`Confirmo o recebimento de ${displayTotalPago}`"
        />
        <div class="flex gap-3 ml-auto">
          <BaseButton variant="secondary" class="px-5" @click="handleCloseFinishModal">Cancelar</BaseButton>
          <BaseButton
            variant="primary"
            :is-loading="finishMutation.isPending.value"
            :disabled="!canFinishWithConfirmation"
            class="px-6 shadow-lg shadow-blue-600/20"
            @click="handleFinish"
          >
            Finalizar Venda
          </BaseButton>
        </div>
      </div>

    </div>
    <template #footer><span></span></template>
  </BaseModal>

  <!-- Sub-modal: Detalhes do pagamento -->
  <BaseModal
    :is-open="showPaymentDetails && !!currentPaymentMethod"
    :title="currentPaymentMethod ? getPaymentDisplayName(currentPaymentMethod.nome) : ''"
    subtitle="Detalhes do pagamento"
    size="sm"
    @close="showPaymentDetails = false"
  >
    <div v-if="currentPaymentMethod" class="space-y-4">
      <div class="flex items-center gap-3 pb-3 border-b border-zinc-100">
        <div class="p-3 bg-brand-primary/10 rounded-xl">
          <component :is="getPaymentIcon(getMethodTipo(currentPaymentMethod))" :size="22" class="text-brand-primary" />
        </div>
        <div>
          <p class="font-bold text-zinc-800">{{ getPaymentDisplayName(currentPaymentMethod.nome) }}</p>
          <p class="text-xs text-zinc-500">Restante: {{ formatCurrency(restante) }}</p>
        </div>
      </div>

      <BaseMoneyInput
        ref="moneyInputRef"
        v-model="paymentValueReais"
        label="Inserir Valor"
        @enter="confirmAddPayment"
      />

      <!-- Parcelamento (cartão de crédito / boleto) -->
      <div v-if="displayParcelasFor(currentPaymentMethod)">
        <BaseSelect
          v-model="paymentDetails.parcelas"
          label="Parcelamento"
          :options="parcelasOptions"
        />
      </div>

      <!-- Boleto: data de vencimento -->
      <div v-if="getMethodTipo(currentPaymentMethod) === 'BOLETO'" class="pt-1">
        <BaseDateInput
          v-model="paymentDetails.vencimento"
          label="Data de Vencimento"
        />
      </div>

      <!-- Cartão: bandeira + taxa de juros -->
      <div v-if="getMethodTipo(currentPaymentMethod).includes('CARTAO')" class="space-y-3">
        <BaseSelect
          v-model="paymentDetails.bandeira"
          label="Bandeira (Opcional)"
          :options="[
            { value: '', label: 'Não informada' },
            { value: 'VISA', label: 'Visa' },
            { value: 'MASTERCARD', label: 'Mastercard' },
            { value: 'ELO', label: 'Elo' },
            { value: 'OUTROS', label: 'Outros' },
          ]"
        />
        <div class="flex justify-between items-center gap-3">
          <label class="text-sm font-medium text-zinc-600 flex items-center gap-1.5">
            <Percent :size="14" /> Taxa de Juros
          </label>
          <div class="w-24">
            <BaseInput
              v-model="jurosTaxaInput"
              type="text"
              inputmode="decimal"
              placeholder="0"
              @blur="normalizarJuros()"
            />
          </div>
        </div>

        <div v-if="jurosAtivo" class="space-y-2">
          <BaseSelect
            v-model="jurosResponsavel"
            label="Quem paga o juros"
            :options="JUROS_RESPONSAVEL_OPTIONS"
          />
          <div
            class="flex justify-between text-xs px-3 py-2 rounded-lg"
            :class="jurosLojaAbsorve ? 'text-rose-600 bg-rose-50' : 'text-amber-600 bg-amber-50'"
          >
            <span>{{ jurosLojaAbsorve ? 'Cliente paga' : 'Valor com juros' }}</span>
            <span class="font-semibold">{{ formatCurrency(valorCobradoDoCliente) }}</span>
          </div>
          <p v-if="jurosLojaAbsorve" class="text-[11px] text-rose-600 px-1">
            A loja absorve {{ formatCurrency(jurosDoPagamentoAtual) }} de juros — o cliente não é
            cobrado a mais e o recebimento da loja fica menor.
          </p>
        </div>
      </div>

      <!-- Transferência: conta de destino + NSU -->
      <div v-if="getMethodTipo(currentPaymentMethod).includes('TRANSFERENCIA')" class="space-y-3">
        <BaseSelect
          v-model="paymentDetails.banco_destino"
          label="Conta de Destino (Opcional)"
          :options="[
            { value: '', label: 'Não informada' },
            { value: 'ITAU', label: 'Itaú' },
            { value: 'BRADESCO', label: 'Bradesco' },
            { value: 'BB', label: 'Banco do Brasil' },
            { value: 'CAIXA', label: 'Caixa Econômica' },
            { value: 'SICREDI', label: 'Sicredi' },
            { value: 'NUBANK', label: 'Nubank' },
            { value: 'OUTROS', label: 'Outros' },
          ]"
        />
        <BaseInput
          v-model="paymentDetails.codigo_transacao"
          type="text"
          label="Código da Transação/NSU (Opcional)"
          placeholder="Ex: E123456789"
        />
      </div>

      <!-- PIX: QR placeholder -->
      <div v-if="getMethodTipo(currentPaymentMethod) === 'PIX'" class="text-center py-2">
        <div class="border-2 border-dashed border-emerald-400/40 bg-emerald-50 rounded-xl p-4 inline-block">
          <QrCode :size="44" class="text-emerald-600" />
        </div>
        <p class="text-[10px] text-zinc-400 mt-2">QR Code para cobrança via PIX.</p>
      </div>

      <div class="flex gap-3 pt-2">
        <BaseButton variant="secondary" class="flex-1" type="button" @click="showPaymentDetails = false">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="flex-1"
          type="button"
          :disabled="paymentValueReais <= 0"
          @click="confirmAddPayment"
        >
          Confirmar
        </BaseButton>
      </div>
    </div>

    <template #footer><span></span></template>
  </BaseModal>
</template>
