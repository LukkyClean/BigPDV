<script setup lang="ts">
/**
 * @component FiscalFechamentoSection
 * @description O bloco fiscal do fechamento de venda no PDV.
 *
 * Responde tres perguntas do caixa, nesta ordem:
 *   1. "Emite cupom fiscal ou é venda gerencial?"
 *   2. "Quer CPF na nota?"
 *   3. "Como essa venda aconteceu?" (indPres da NFC-e)
 *
 * Vive num componente separado do FinishSaleModal de propósito: aquele arquivo
 * já passa de 900 linhas cuidando de pagamentos, e a regra fiscal muda por
 * motivo diferente (legislação) do fluxo de recebimento.
 */

import { computed, nextTick, ref, watch } from 'vue';
import { cpf as cpfValidator, cnpj as cnpjValidator } from 'cpf-cnpj-validator';
import { Receipt, FileX, AlertTriangle, Loader2 } from 'lucide-vue-next';

import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { formatCPF, formatCNPJ, unmaskDocument } from '@/shared/utils/document.utils';
import { formatCurrency } from '@/shared/utils/finance';
import { recursoDisponivel } from '@/shared/config/planos';
import { useFiscalConfiguracaoQuery } from '@/modules/fiscal/composables/useFiscalConfiguracaoQuery';

const props = defineProps<{
  /** Total da venda em centavos — decide o bloqueio do consumidor anônimo. */
  totalCentavos: number;
  /** Documento do cliente já cadastrado na venda, se houver (só dígitos). */
  documentoCliente?: string | null;
}>();

const emit = defineEmits<{
  (e: 'update:emitirFiscal', valor: boolean): void;
  (e: 'update:documento', valor: string | null): void;
  /** indPres da NFC-e — ver INDICADOR_PRESENCA_OPTIONS. */
  (e: 'update:indicadorPresenca', valor: number): void;
  /** True quando algo impede finalizar — o modal desabilita o botão. */
  (e: 'update:bloqueado', valor: boolean): void;
}>();

const moduloDisponivel = recursoDisponivel('nfe');

const { data: configuracao, isLoading } = useFiscalConfiguracaoQuery();

const emitirFiscal = ref(false);
const documentoDigitado = ref('');

// ── Indicador de presença (indPres) ──────────────────────────────────────
// Campo obrigatório do layout da NFC-e. Até aqui o PDV nunca o preenchia e
// TODA NFC-e saía com 1 (presencial), porque é o default do payload_builder.
// Certo no balcão, errado justamente no delivery — que é o indPres 4, o valor
// que só existe para NFC-e.
//
// Não pode virar mais uma pergunta no caminho crítico: o fechamento é de
// quatro teclas e o cliente está esperando. Por isso nasce em "Balcão", que
// cobre a esmagadora maioria das vendas, e só quem foge do padrão mexe.
//
// Uma escolha errada aqui não é cosmética: indPres alimenta a trava
// interestadual do resolver (_operacao_presencial). Marcar "Balcão" numa venda
// que na verdade foi pela internet desliga a trava e libera uma nota
// interestadual sem DIFAL.
const INDICADOR_PRESENCA_OPTIONS = [
  { value: 1, label: 'Balcão (cliente presente)' },
  { value: 4, label: 'Entrega a domicílio' },
  { value: 2, label: 'Internet / WhatsApp' },
  { value: 3, label: 'Telefone' },
  { value: 9, label: 'Outro' },
];
const INDICADOR_PRESENCA_BALCAO = 1;

// `string | number` porque é o que o BaseSelect expõe no v-model; a
// normalização para number acontece na saída, num lugar só.
const indicadorPresenca = ref<string | number>(INDICADOR_PRESENCA_BALCAO);
watch(
  indicadorPresenca,
  (v) => emit('update:indicadorPresenca', Number(v) || INDICADOR_PRESENCA_BALCAO),
  { immediate: true },
);
const documentoInputRef = ref<InstanceType<typeof BaseInput> | null>(null);

// ── Documento efetivo ────────────────────────────────────────────────────
// O cadastro do cliente vence o digitado: foi conferido uma vez. Mesma
// precedência do backend (`_documento_do_consumidor`), para a tela não
// prometer um bloqueio que o servidor não aplica — nem o contrário.
const documentoDoCliente = computed(() => unmaskDocument(props.documentoCliente ?? ''));
const documentoDigitadoLimpo = computed(() => unmaskDocument(documentoDigitado.value));
const documentoEfetivo = computed(
  () => documentoDoCliente.value || documentoDigitadoLimpo.value,
);

const documentoValido = computed(() => {
  const doc = documentoEfetivo.value;
  if (doc.length === 11) return cpfValidator.isValid(doc);
  if (doc.length === 14) return cnpjValidator.isValid(doc);
  return false;
});

/** Máscara dinâmica: vira CNPJ sozinha ao passar de 11 dígitos. */
const documentoFormatado = computed(() => {
  const doc = documentoDigitadoLimpo.value;
  if (doc.length <= 11) return formatCPF(doc);
  return formatCNPJ(doc);
});

const erroDocumento = computed(() => {
  const doc = documentoDigitadoLimpo.value;
  if (!doc) return '';                       // vazio é o caso normal do balcão
  if (doc.length < 11) return '';             // ainda digitando
  if (doc.length === 11 && !cpfValidator.isValid(doc)) return 'CPF inválido';
  if (doc.length > 11 && doc.length < 14) return '';
  if (doc.length === 14 && !cnpjValidator.isValid(doc)) return 'CNPJ inválido';
  return '';
});

/**
 * Quem configurou a NFC-e quer emitir — o padrão segue a configuração da loja
 * em vez de obrigar um clique por venda. Só se aplica UMA vez, e nunca depois
 * de o operador escolher: a decisão dele vence a heurística.
 */
const escolhaManual = ref(false);
watch(
  () => configuracao.value,
  (config) => {
    if (!config || escolhaManual.value) return;
    emitirFiscal.value = Boolean(config.certificado_valido && config.csc_configurado);
  },
  { immediate: true },
);

async function escolher(fiscal: boolean) {
  escolhaManual.value = true;
  emitirFiscal.value = fiscal;

  // Ao escolher fiscal, o próximo passo é sempre "quer CPF?" — levar o cursor
  // até lá poupa o operador de procurar o campo com o cliente esperando.
  if (fiscal && !documentoDoCliente.value) {
    await nextTick();
    focarDocumento();
  }
}

function focarDocumento() {
  const el = (documentoInputRef.value?.$el as HTMLElement | undefined)
    ?.querySelector('input');
  el?.focus();
  el?.select();
}



// ── Regra 3: teto do consumidor anônimo ──────────────────────────────────
const limite = computed(() => configuracao.value?.limite_consumidor_anonimo ?? 1000000);

const exigeDocumento = computed(
  () => limite.value > 0 && props.totalCentavos >= limite.value,
);

const faltaDocumentoObrigatorio = computed(
  () => emitirFiscal.value && exigeDocumento.value && !documentoValido.value,
);

// ── Impedimentos de configuração ─────────────────────────────────────────
const cscAusente = computed(
  () => emitirFiscal.value && configuracao.value != null && !configuracao.value.csc_configurado,
);

const certificadoInvalido = computed(
  () => emitirFiscal.value && configuracao.value != null && !configuracao.value.certificado_valido,
);

const bloqueado = computed(
  () =>
    faltaDocumentoObrigatorio.value ||
    cscAusente.value ||
    certificadoInvalido.value ||
    !!erroDocumento.value,
);

const homologacao = computed(() => configuracao.value?.ambiente === 2);

// ── Sincronização com o pai ──────────────────────────────────────────────
watch(emitirFiscal, (v) => emit('update:emitirFiscal', v), { immediate: true });
watch(bloqueado, (v) => emit('update:bloqueado', v), { immediate: true });
watch(documentoDigitadoLimpo, (doc) => {
  emit('update:documento', documentoValido.value && doc ? doc : null);
});

function aoDigitarDocumento(valor: string | number) {
  // Guarda só dígitos e reaplica a máscara na exibição — assim apagar no meio
  // do número não deixa a pontuação órfã.
  documentoDigitado.value = unmaskDocument(String(valor)).slice(0, 14);
}
</script>

<template>
  <div v-if="moduloDisponivel" class="rounded-xl border border-zinc-200 bg-white p-3 space-y-3">
    <!-- Escolha: fiscal ou gerencial -->
    <div class="flex items-center gap-2">
      <button
        type="button"
        data-emitir-fiscal
        :class="[
          'flex-1 flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-xs font-bold transition-colors cursor-pointer',
          emitirFiscal
            ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
            : 'border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50',
        ]"
        @click="escolher(true)"
      >
        <Receipt :size="15" />
        Emitir Fiscal
      </button>
      <button
        type="button"
        data-venda-gerencial
        :class="[
          'flex-1 flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-xs font-bold transition-colors cursor-pointer',
          !emitirFiscal
            ? 'border-zinc-300 bg-zinc-100 text-zinc-700'
            : 'border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50',
        ]"
        @click="escolher(false)"
      >
        <FileX :size="15" />
        Venda Gerencial
      </button>
    </div>

    <!-- CPF na nota -->
    <template v-if="emitirFiscal">
      <div v-if="documentoDoCliente" class="text-xs text-zinc-500">
        Cliente identificado:
        <span class="font-semibold text-zinc-700 tabular-nums">
          {{ documentoDoCliente.length === 11
            ? formatCPF(documentoDoCliente)
            : formatCNPJ(documentoDoCliente) }}
        </span>
      </div>

      <BaseInput
        v-else
        ref="documentoInputRef"
        data-cpf-na-nota
        :model-value="documentoFormatado"
        label="CPF/CNPJ na nota (opcional)"
        placeholder="Deixe em branco para consumidor não identificado"
        inputmode="numeric"
        :error="erroDocumento"
        @update:model-value="aoDigitarDocumento"
      />

      <!--
        Como a venda aconteceu. Nasce em "Balcão": o caminho feliz não ganha
        nenhum passo, e quem faz delivery corrige em um clique.
      -->
      <BaseSelect
        v-model="indicadorPresenca"
        data-indicador-presenca
        label="Como foi esta venda"
        :options="INDICADOR_PRESENCA_OPTIONS"
      />

      <!-- Avisos, do mais bloqueante ao informativo -->
      <div
        v-if="certificadoInvalido"
        class="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2"
      >
        <AlertTriangle :size="14" class="text-red-500 mt-0.5 shrink-0" />
        <p class="text-[11px] text-red-700 leading-snug">
          Certificado digital ausente ou vencido. Configure em
          <strong>Centro Fiscal</strong> ou finalize como venda gerencial.
        </p>
      </div>

      <div
        v-else-if="cscAusente"
        class="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2"
      >
        <AlertTriangle :size="14" class="text-red-500 mt-0.5 shrink-0" />
        <p class="text-[11px] text-red-700 leading-snug">
          O CSC não está configurado — sem ele o cupom sai sem QR Code válido.
          Cadastre em <strong>Centro Fiscal</strong>.
        </p>
      </div>

      <div
        v-else-if="faltaDocumentoObrigatorio"
        class="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2"
      >
        <AlertTriangle :size="14" class="text-amber-500 mt-0.5 shrink-0" />
        <p class="text-[11px] text-amber-800 leading-snug">
          Vendas a partir de <strong>{{ formatCurrency(limite) }}</strong> exigem o
          CPF ou CNPJ do comprador na NFC-e.
        </p>
      </div>

      <div v-else-if="isLoading" class="flex items-center gap-2 text-[11px] text-zinc-400">
        <Loader2 :size="12" class="animate-spin" />
        Conferindo a configuração fiscal…
      </div>

      <p v-else-if="homologacao" class="text-[11px] text-amber-600">
        Ambiente de <strong>homologação</strong> — o cupom sai sem valor fiscal.
      </p>
    </template>
  </div>
</template>
