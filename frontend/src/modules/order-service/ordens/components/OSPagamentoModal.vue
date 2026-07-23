<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import {
  FileText, CreditCard, Wallet, QrCode,
  Banknote, Trash2, Percent, Tag, Truck, ArrowLeft, CheckCircle2, RotateCcw,
} from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import type { PaymentFormReadDataType } from '@/shared/schemas/payments/payment.schema';
import type { OsCardsFlagEnumDataType } from '../schemas/enums/osEnums.schema';
import type { DadosFinalizacaoOS } from './OSFinalizarModal.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { useOsPaymentMethodsGet } from '../composables/request/relationship/useOSPaymentMethods.queries';
import { useReadyOrderServiceMutation } from '../composables/request/useOrderServiceUpdate.mutate';
import { inferPaymentType, inferPermiteParcelamento, getPaymentDisplayName } from '../../shared/utils/formatters';

interface Pagamento {
  forma_pagamento_id: number;
  valor: number;
  parcelas: number;
  bandeira_cartao?: OsCardsFlagEnumDataType;
  vencimento?: string;
  detalhes?: string;
}

interface Props {
  isOpen: boolean;
  osNumero: string | null;
  ordemServico: OrderServiceReadDataType | null;
  dadosOs: DadosFinalizacaoOS | null;
  descontoOs: number;
  creditoAoReabrir?: number | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  voltar: [];
  finalized: [payload: { shouldPrint: boolean }];
}>();

// ─── Dados externos ───────────────────────────────────────────────────────────
const { formasPagamento } = useOsPaymentMethodsGet();
const finalizarMutation = useReadyOrderServiceMutation();

// ─── Estado ──────────────────────────────────────────────────────────────────
const pagamentos = ref<Pagamento[]>([]);
const pagamentosJuros = ref<number[]>([]);
const confirmacao = ref(false);
const hasAttemptedSubmit = ref(false);

const moneyInputRef = ref();

const showPaymentDetails = ref(false);
const currentPaymentMethod = ref<PaymentFormReadDataType | null>(null);
const paymentDetails = ref<{
  parcelas: number;
  bandeira: OsCardsFlagEnumDataType | '';
  taxa_juros: number;
  vencimento?: string;
  banco_destino?: string;
  codigo_transacao?: string;
}>({ parcelas: 1, bandeira: '', taxa_juros: 0, vencimento: new Date().toISOString().split('T')[0], banco_destino: '', codigo_transacao: '' });
const paymentValueReais = ref(0);

const parcelasOptions = computed(() => {
  const options = [{ value: 1, label: 'À vista' }];
  const baseValor = Math.round(paymentValueReais.value * 100);
  const jurosAmount = Math.round(baseValor * (paymentDetails.value.taxa_juros / 100));
  const totalParcelar = baseValor + jurosAmount;

  for (let i = 2; i <= 12; i++) {
    const valorParcela = totalParcelar / i;
    options.push({
      value: i,
      label: `${i}x de ${formatCurrency(Math.round(valorParcela))}`
    });
  }
  return options;
});

// ─── Cálculos financeiros ─────────────────────────────────────────────────────
const subtotalItens = computed(() => {
  if (!props.ordemServico?.itens) return 0;
  return props.ordemServico.itens.reduce((sum, item) => sum + item.valor_total, 0);
});

const desconto = computed(() => props.descontoOs);
const taxaEntrega = computed(() => props.ordemServico?.taxa_entrega ?? 0);
const valorEntrada = computed(() => props.ordemServico?.valor_entrada ?? 0);
const creditoAoReabrir = computed(() => props.creditoAoReabrir ?? null);
const acrescimoTotal = computed(() => pagamentosJuros.value.reduce((sum, v) => sum + v, 0));

// Desconto já acumulado na OS. O `descontoOs` recebido é só o desconto ADICIONAL
// desta finalização; sem somar o existente aqui, o "Total a pagar" ignorava o
// desconto antigo e cobrava a mais (ex.: 190 − 10 = 180 em vez de 190 − 20 − 10 =
// 160). É sempre o os.desconto atual (o backend acumula em cima dele) — NÃO amarrar
// ao credito_anterior: na reabertura "não pagou" o crédito é zerado mas o desconto
// permanece, e amarrar fazia voltar a cobrar a mais.
const existingDesconto = computed(() => props.ordemServico?.desconto ?? 0);

const valorTotal = computed(() =>
  Math.max(
    0,
    subtotalItens.value - existingDesconto.value - desconto.value + taxaEntrega.value + acrescimoTotal.value,
  ),
);

// Pagamentos de finalizações anteriores (preservados após reopen)
const pagamentosAnteriores = computed(() => props.ordemServico?.pagamentos ?? []);
const totalPagamentosAnteriores = computed(() => {
  if (creditoAoReabrir.value != null) {
    // credito_anterior = total histórico pago (pagamentos + entrada anterior) — só display
    return creditoAoReabrir.value;
  }
  return pagamentosAnteriores.value.reduce((sum, p) => sum + p.valor, 0);
});

const totalAReceber = computed(() =>
  Math.max(0, valorTotal.value - valorEntrada.value - totalPagamentosAnteriores.value),
);
const totalPago = computed(() => pagamentos.value.reduce((sum, p) => sum + p.valor, 0));
const restante = computed(() => Math.max(0, totalAReceber.value - totalPago.value));
const troco = computed(() => Math.max(0, totalPago.value - totalAReceber.value));
const canSubmit = computed(() => confirmacao.value && restante.value === 0);

// ─── Valor alocado por forma de pagamento ─────────────────────────────────────
function getValorPorMetodo(formaId: number): number {
  return pagamentos.value
    .filter(p => p.forma_pagamento_id === formaId)
    .reduce((sum, p) => sum + p.valor, 0);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getMethodTipo(method: PaymentFormReadDataType): string {
  return method.tipo ?? inferPaymentType(method.nome);
}

function getMethodPermiteParcelamento(method: PaymentFormReadDataType): boolean {
  return method.permite_parcelamento ?? inferPermiteParcelamento(getMethodTipo(method));
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

function getPaymentMethodById(id: number): PaymentFormReadDataType | undefined {
  return formasPagamento.value.find(f => f.id === id);
}

function getPaymentIconById(id: number) {
  const method = getPaymentMethodById(id);
  return getPaymentIcon(method ? getMethodTipo(method) : '');
}

// ─── Pagamentos ───────────────────────────────────────────────────────────────
function handleAddPaymentClick(method: PaymentFormReadDataType) {
  currentPaymentMethod.value = method;
  paymentValueReais.value = restante.value / 100;
  paymentDetails.value = { parcelas: 1, bandeira: '', taxa_juros: 0, vencimento: new Date().toISOString().split('T')[0], banco_destino: '', codigo_transacao: '' };
  showPaymentDetails.value = true;
  
  nextTick(() => {
    if (moneyInputRef.value?.inputRef) {
      moneyInputRef.value.inputRef.select();
    }
  });
}

function confirmAddPayment() {
  if (!currentPaymentMethod.value) return;
  const baseValor = Math.round(paymentValueReais.value * 100);
  const jurosAmount = Math.round(baseValor * (paymentDetails.value.taxa_juros / 100));

  let payloadDetalhes = undefined;
  if (getMethodTipo(currentPaymentMethod.value).includes('TRANSFERENCIA')) {
    if (paymentDetails.value.banco_destino || paymentDetails.value.codigo_transacao) {
      payloadDetalhes = JSON.stringify({
        banco_destino: paymentDetails.value.banco_destino,
        codigo_transacao: paymentDetails.value.codigo_transacao
      });
    }
  }

  pagamentos.value.push({
    forma_pagamento_id: currentPaymentMethod.value.id,
    valor: baseValor + jurosAmount,
    parcelas: paymentDetails.value.parcelas,
    bandeira_cartao: (paymentDetails.value.bandeira || undefined) as OsCardsFlagEnumDataType | undefined,
    vencimento: paymentDetails.value.vencimento,
    detalhes: payloadDetalhes,
  });
  pagamentosJuros.value.push(jurosAmount);
  showPaymentDetails.value = false;
  currentPaymentMethod.value = null;
}

function removePayment(index: number) {
  pagamentos.value.splice(index, 1);
  pagamentosJuros.value.splice(index, 1);
}

function zerarPagamentos() {
  pagamentos.value = [];
  pagamentosJuros.value = [];
  showPaymentDetails.value = false;
  currentPaymentMethod.value = null;
}

// ─── Submit ───────────────────────────────────────────────────────────────────
function handleSubmit() {
  hasAttemptedSubmit.value = true;
  if (!canSubmit.value || !props.osNumero) return;

  finalizarMutation.mutate(
    {
      osNumber: props.osNumero,
      readyOs: {
        situacao_equipamento: props.dadosOs?.situacao_equipamento,
        garantia: props.dadosOs?.garantia,
        solucao: props.dadosOs?.solucao,
        observacoes: props.dadosOs?.observacoes ?? '',
        desconto: desconto.value,
        taxa_entrega: taxaEntrega.value,
        acrescimo: acrescimoTotal.value,
        valor_entrada: valorEntrada.value,
        zerar_adiantamento: props.dadosOs?.zerarAdiantamento ?? false,
        pagamentos: pagamentos.value.map(p => ({
          forma_pagamento_id: p.forma_pagamento_id,
          valor: p.valor,
          parcelas: p.parcelas,
          bandeira_cartao: p.bandeira_cartao,
          vencimento: p.vencimento,
          detalhes: p.detalhes,
        })),
      },
    },
    { onSuccess: () => emit('finalized', { shouldPrint: props.dadosOs?.shouldPrint ?? false }) },
  );
}

// ─── Reset / Init ─────────────────────────────────────────────────────────────
function resetState() {
  pagamentos.value = [];
  pagamentosJuros.value = [];
  confirmacao.value = false;
  hasAttemptedSubmit.value = false;
  showPaymentDetails.value = false;
  currentPaymentMethod.value = null;
}

watch(() => props.isOpen, (open) => {
  if (!open) resetState();
});

watch(() => paymentDetails.value.taxa_juros, (v) => {
  const clamped = Math.min(100, Math.max(0, v ?? 0));
  if (v !== clamped) paymentDetails.value.taxa_juros = clamped;
});
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Pagamento"
    :subtitle="osNumero ? `OS: ${osNumero}` : ''"
    size="3xl"
    :overlay="true"
    overflow="hidden"
    @close="emit('close')"
  >
    <div class="flex flex-col gap-4 h-[calc(90vh-140px)]">

      <!-- ── Linha principal: coluna esq (formas + pagamentos) + coluna dir (resumo) ── -->
      <div class="grid grid-cols-2 gap-4 flex-1 min-h-0">

        <!-- Coluna esquerda: formas de pagamento + lista -->
        <div class="flex flex-col gap-2 min-h-0">

          <!-- Formas de pagamento 3x2 -->
          <div class="shrink-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1.5">Selecionar Forma de Pagamento</p>
            <div class="grid grid-cols-3 gap-1.5">
              <button
                v-for="method in formasPagamento"
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
              <span class="text-[10px] text-zinc-400">{{ pagamentos.length }} item(s)</span>
              <button
                v-if="pagamentos.length > 0"
                type="button"
                class="flex items-center gap-1 text-[10px] text-red-400 hover:text-red-600 transition-colors cursor-pointer"
                @click="zerarPagamentos"
              >
                <RotateCcw :size="11" />
                Zerar
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-3 space-y-2">
            <div v-if="pagamentos.length === 0" class="h-full flex items-center justify-center py-8">
              <p class="text-xs text-zinc-400">Nenhum pagamento registrado</p>
            </div>

            <div
              v-for="(pgto, idx) in pagamentos"
              :key="idx"
              class="flex items-center justify-between p-2.5 bg-white border border-zinc-100 rounded-lg shadow-sm"
            >
              <div class="flex items-center gap-2.5">
                <div class="p-1.5 bg-zinc-50 rounded-lg text-brand-primary">
                  <component :is="getPaymentIconById(pgto.forma_pagamento_id)" :size="14" />
                </div>
                <div>
                  <p class="text-xs font-semibold text-zinc-700">
                    {{ getPaymentDisplayName(getPaymentMethodById(pgto.forma_pagamento_id)?.nome ?? 'Pagamento') }}
                    <span v-if="pgto.parcelas > 1" class="font-normal text-zinc-400"> · {{ pgto.parcelas }}x</span>
                  </p>
                  <template v-if="pagamentosJuros[idx] > 0">
                    <p class="text-[10px] text-zinc-400">
                      Serviço: {{ formatCurrency(pgto.valor - pagamentosJuros[idx]) }}
                      <span class="text-amber-500"> + Juros: {{ formatCurrency(pagamentosJuros[idx]) }}</span>
                      = {{ formatCurrency(pgto.valor) }}
                    </p>
                  </template>
                  <template v-else>
                    <p class="text-[10px] text-zinc-400">{{ formatCurrency(pgto.valor) }}</p>
                  </template>
                </div>
              </div>
              <button type="button" @click="removePayment(idx)" class="text-zinc-300 hover:text-red-500 p-1.5 cursor-pointer transition-colors">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>

          <div v-if="hasAttemptedSubmit && pagamentos.length === 0 && totalPagamentosAnteriores === 0 && totalAReceber > 0"
            class="px-3 pb-2 text-[10px] text-red-500 shrink-0">
            Adicione ao menos uma forma de pagamento.
          </div>
        </div>

        </div><!-- fim coluna esquerda -->

        <!-- Resumo financeiro -->
        <div class="border border-zinc-200 rounded-xl overflow-hidden flex flex-col">
          <div class="bg-zinc-100 px-4 py-2 border-b border-zinc-200">
            <p class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Resumo Financeiro</p>
          </div>
          <div class="p-4 space-y-2.5 overflow-y-auto flex-1 no-scrollbar">

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Valor OS</span>
              <span class="text-base font-semibold text-zinc-800">{{ formatCurrency(subtotalItens) }}</span>
            </div>

            <div v-if="existingDesconto > 0" class="flex justify-between items-center">
              <span class="text-xs text-zinc-500 flex items-center gap-1">
                <Tag :size="12" /> Desconto anterior
              </span>
              <span class="text-base font-semibold text-emerald-600">- {{ formatCurrency(existingDesconto) }}</span>
            </div>

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500 flex items-center gap-1">
                <Tag :size="12" /> {{ existingDesconto > 0 ? 'Desconto adicional' : 'Desconto' }}
              </span>
              <span class="text-base" :class="desconto > 0 ? 'font-semibold text-emerald-600' : 'font-medium text-zinc-400'">
                {{ desconto > 0 ? `- ${formatCurrency(desconto)}` : '—' }}
              </span>
            </div>

            <div v-if="taxaEntrega > 0" class="flex justify-between items-center">
              <span class="text-xs text-zinc-500 flex items-center gap-1">
                <Truck :size="12" /> Deslocamento
              </span>
              <span class="text-base font-medium text-zinc-700">{{ formatCurrency(taxaEntrega) }}</span>
            </div>

            <div v-if="valorEntrada > 0" class="flex justify-between items-center">
              <span class="text-xs text-emerald-600 flex items-center gap-1">
                <CheckCircle2 :size="12" /> Adiantamento
              </span>
              <span class="text-base font-semibold text-emerald-600">- {{ formatCurrency(valorEntrada) }}</span>
            </div>

            <div v-if="totalPagamentosAnteriores > 0" class="flex justify-between items-center">
              <span class="text-xs text-emerald-600 flex items-center gap-1">
                <CheckCircle2 :size="12" /> Pago anteriormente
              </span>
              <span class="text-base font-semibold text-emerald-600">- {{ formatCurrency(totalPagamentosAnteriores) }}</span>
            </div>

            <div v-if="acrescimoTotal > 0" class="flex justify-between items-center">
              <span class="text-xs text-amber-600 flex items-center gap-1">
                <Percent :size="12" /> Juros
              </span>
              <span class="text-base font-medium text-amber-600">+ {{ formatCurrency(acrescimoTotal) }}</span>
            </div>

            <!-- Divisor -->
            <div class="border-t border-zinc-200 pt-2.5 space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-bold text-zinc-700">Total a pagar</span>
                <span class="text-xl font-bold text-brand-primary">{{ formatCurrency(valorTotal) }}</span>
              </div>

              <div v-if="valorEntrada > 0" class="flex justify-between items-center text-xs text-zinc-500">
                <span>Adiantamento</span>
                <span>- {{ formatCurrency(valorEntrada) }}</span>
              </div>

              <div class="flex justify-between items-center font-semibold"
                :class="totalPago >= totalAReceber ? 'text-emerald-600' : 'text-zinc-400'">
                <span class="text-sm">Total recebido</span>
                <span class="text-lg">{{ formatCurrency(totalPago) }}</span>
              </div>

              <!-- Breakdown de devolução (só exibe quando há juros) -->
              <div v-if="acrescimoTotal > 0 && totalPago > 0" class="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 space-y-1">
                <p class="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">Em caso de devolução</p>
                <div class="flex justify-between items-center text-xs text-zinc-600">
                  <span>Serviço (dinheiro)</span>
                  <span class="font-semibold">{{ formatCurrency(totalPago - acrescimoTotal) }}</span>
                </div>
                <div class="flex justify-between items-center text-xs text-zinc-600">
                  <span>Estorno cartão (total pago)</span>
                  <span class="font-semibold">{{ formatCurrency(totalPago) }}</span>
                </div>
                <p class="text-[10px] text-amber-600">Juros pagos à operadora: {{ formatCurrency(acrescimoTotal) }}</p>
              </div>

              <div v-if="restante > 0" class="flex justify-between items-center font-bold text-red-500">
                <span class="text-sm">Faltam</span>
                <span class="text-lg">{{ formatCurrency(restante) }}</span>
              </div>

              <div v-if="troco > 0" class="flex justify-between items-center font-bold text-amber-500">
                <span class="text-sm">Troco</span>
                <span class="text-lg">{{ formatCurrency(troco) }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ── Linha 3: Confirmação + botões ── -->
      <div class="flex items-center gap-4 pt-3 border-t border-zinc-200 shrink-0">
        <BaseCheckbox
          v-model="confirmacao"
          :label="`Confirmo a conclusão e recebimento (${formatCurrency(totalPago)})`"
        />
        <div class="flex gap-3 ml-auto">
          <BaseButton
            type="button"
            variant="secondary"
            class="px-5 py-2.5"
            @click="emit('voltar')"
          >
            <ArrowLeft :size="15" class="mr-1.5" />
            Voltar
          </BaseButton>
          <BaseButton
            type="button"
            variant="primary"
            :is-loading="finalizarMutation.isPending.value"
            :disabled="!canSubmit"
            class="px-6 py-2.5 shadow-lg shadow-blue-600/20"
            @click="handleSubmit"
          >
            Finalizar OS
          </BaseButton>
        </div>
      </div>

    </div>
    <template #footer><span></span></template>
  </BaseModal>

  <!-- ── Sub-modal: detalhes do pagamento ── -->
  <BaseModal
    :is-open="showPaymentDetails && !!currentPaymentMethod"
    :title="currentPaymentMethod ? getPaymentDisplayName(currentPaymentMethod.nome) : ''"
    subtitle="Detalhes do pagamento"
    size="sm"
    :overlay="true"
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

      <div v-if="getMethodPermiteParcelamento(currentPaymentMethod) || getMethodTipo(currentPaymentMethod) === 'BOLETO'" class="space-y-3">
        <BaseSelect
          v-model="paymentDetails.parcelas"
          label="Parcelamento"
          :options="parcelasOptions"
        />
      </div>

      <div v-if="getMethodTipo(currentPaymentMethod) === 'BOLETO'" class="pt-1">
        <BaseDateInput
          v-model="paymentDetails.vencimento"
          label="Data de Vencimento"
        />
      </div>

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
            <BaseInput v-model="paymentDetails.taxa_juros" type="number" placeholder="0" />
          </div>
        </div>
        <div v-if="paymentDetails.taxa_juros > 0" class="flex justify-between text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
          <span>Valor com juros</span>
          <span class="font-semibold">
            {{ formatCurrency(Math.round(paymentValueReais * 100 * (1 + paymentDetails.taxa_juros / 100))) }}
          </span>
        </div>
      </div>

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
            { value: 'OUTROS', label: 'Outros' }
          ]"
        />
        <BaseInput 
          v-model="paymentDetails.codigo_transacao" 
          type="text" 
          label="Código da Transação/NSU (Opcional)" 
          placeholder="Ex: E123456789"
        />
      </div>

      <div v-if="getMethodTipo(currentPaymentMethod) === 'PIX'" class="text-center py-2">
        <div class="border-2 border-dashed border-emerald-400/40 bg-emerald-50 rounded-xl p-4 inline-block">
          <QrCode :size="44" class="text-emerald-600" />
        </div>
        <p class="text-[10px] text-zinc-400 mt-2">QR Code para cobrança via PIX.</p>
      </div>

      <div class="flex gap-3 pt-2">
        <BaseButton variant="secondary" class="flex-1" @click="showPaymentDetails = false">Cancelar</BaseButton>
        <BaseButton variant="primary" class="flex-1" @click="confirmAddPayment">Confirmar</BaseButton>
      </div>
    </div>
    <template #footer><span></span></template>
  </BaseModal>
</template>
