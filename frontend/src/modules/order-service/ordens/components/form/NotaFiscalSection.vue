<script setup lang="ts">
/**
 * @component NotaFiscalSection (OS)
 * @description Seção de nota fiscal para Ordem de Serviço.
 *
 * A OS pode gerar dois documentos distintos:
 * - NFe/NFCe para itens de produto (peças)
 * - NFSe para itens de serviço (mão de obra)
 *
 * Dois modos:
 * - Edição (OS editável): campos configuráveis + flags de emissão.
 * - Visualização (OS finalizada/cancelada): status NFe e NFSe exibidos separadamente.
 *
 * O save fiscal é chamado pelo pai (OSFormModal) via provide/inject
 * no onUpdateSuccess — não possui botão de salvar próprio.
 */

import { watch, computed } from 'vue';
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';
import { z } from 'zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query';
import { FileText, Info, Send } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import PendenciasFiscaisModal from '@/shared/components/commons/PendenciasFiscaisModal.vue';
import { useToast } from '@/shared/composables/useToast';
import { useEmitirFiscal } from '@/shared/composables/useEmitirFiscal';
import { getOsNotaFiscal, upsertOsNotaFiscal } from '../../services/orderServiceFiscal.service';
import type { OsNotaFiscalUpdate } from '../../types/notaFiscal.type';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';
import { OS_NOTA_FISCAL_QUERY_KEY } from '../../constants/core.constant';
import { registerOSFiscalSave } from '../../composables/modal/useOSFiscalSave';

// =============================================
// Props
// =============================================

interface Props {
  osNumero: string;
  osStatus: string;
}

const props = defineProps<Props>();

// =============================================
// Constants
// =============================================

const FINALIDADE_OPTIONS = [
  { value: 1, label: '1 — Normal' },
  { value: 2, label: '2 — Complementar' },
  { value: 3, label: '3 — Ajuste' },
  { value: 4, label: '4 — Devolução/Retorno' },
];

const INDICADOR_OPTIONS = [
  { value: 1, label: '1 — Presencial' },
  { value: 2, label: '2 — Internet' },
  { value: 3, label: '3 — Teleatendimento' },
  { value: 4, label: '4 — Entrega domiciliar' },
  { value: 9, label: '9 — Outros' },
];

const STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  PENDENTE: { bg: 'bg-amber-100', text: 'text-amber-700' },
  EMITIDA: { bg: 'bg-green-100', text: 'text-green-700' },
  CANCELADA: { bg: 'bg-zinc-100', text: 'text-zinc-500' },
  DENEGADA: { bg: 'bg-red-100', text: 'text-red-600' },
  ERRO: { bg: 'bg-red-100', text: 'text-red-600' },
};

function getBadge(status?: string | null) {
  return STATUS_BADGE[status ?? 'PENDENTE'] ?? STATUS_BADGE.PENDENTE;
}

// =============================================
// State
// =============================================

const STATUSES_LOCKED = ['FINALIZADA', 'CANCELADA'];
const isEditing = computed(() => !STATUSES_LOCKED.includes(props.osStatus));

// =============================================
// Schema Zod + Form (VeeValidate)
// =============================================

const osNotaFiscalSchema = z.object({
  natureza_operacao: z.string().max(60).nullable().optional(),
  finalidade_emissao: z.number().int().nullable().optional(),
  consumidor_final: z.boolean().default(true),
  indicador_presenca: z.number().int().nullable().optional(),
  emitir_nfe: z.boolean().default(true),
  emitir_nfse: z.boolean().default(true),
});

const { defineField, setValues } = useForm({
  validationSchema: toTypedSchema(osNotaFiscalSchema),
  initialValues: { consumidor_final: true, emitir_nfe: true, emitir_nfse: true },
});

const [natureza_operacao] = defineField('natureza_operacao');
const [finalidade_emissao] = defineField('finalidade_emissao');
const [consumidor_final] = defineField('consumidor_final');
const [indicador_presenca] = defineField('indicador_presenca');
const [emitir_nfe] = defineField('emitir_nfe');
const [emitir_nfse] = defineField('emitir_nfse');

// =============================================
// Query
// =============================================

const queryClient = useQueryClient();
const toast = useToast();

const { data: notaFiscal } = useQuery({
  queryKey: computed(() => [OS_NOTA_FISCAL_QUERY_KEY, props.osNumero]),
  queryFn: () => getOsNotaFiscal(props.osNumero),
  staleTime: 1000 * 60,
});

watch(notaFiscal, (nota) => {
  if (!nota) return;
  setValues({
    natureza_operacao: nota.natureza_operacao ?? '',
    finalidade_emissao: nota.finalidade_emissao ?? undefined,
    consumidor_final: nota.consumidor_final ?? true,
    indicador_presenca: nota.indicador_presenca ?? undefined,
    emitir_nfe: nota.emitir_nfe ?? true,
    emitir_nfse: nota.emitir_nfse ?? true,
  } as any, false);
}, { immediate: true });

// =============================================
// Mutation + saveFiscal exposto via provide/inject
// =============================================

const { mutateAsync: salvar } = useMutation({
  mutationFn: (dados: OsNotaFiscalUpdate) => upsertOsNotaFiscal(props.osNumero, dados),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: [OS_NOTA_FISCAL_QUERY_KEY, props.osNumero] });
  },
  onError: (err: AxiosError<ApiError>) => {
    toast.error(getErrorMessage(err));
  },
});

async function saveFiscal() {
  if (!isEditing.value) return;
  await salvar({
    natureza_operacao: natureza_operacao.value || null,
    finalidade_emissao: finalidade_emissao.value ?? null,
    consumidor_final: consumidor_final.value,
    indicador_presenca: indicador_presenca.value ?? null,
    emitir_nfe: emitir_nfe.value,
    emitir_nfse: emitir_nfse.value,
  });
}

// Registra a função de save no contexto do pai para ser chamada no onUpdateSuccess
registerOSFiscalSave(saveFiscal);

// =============================================
// Emissão Fiscal
// =============================================

const { pendencias, pendenciasModalOpen, isVerificando, emitirOS } = useEmitirFiscal();

const podeEmitirNfe = computed(() => {
  if (props.osStatus !== 'FINALIZADA') return false;
  const statusNfe = notaFiscal.value?.status_nfe ?? 'PENDENTE';
  const emitir = notaFiscal.value?.emitir_nfe ?? true;
  return emitir && (statusNfe === 'PENDENTE' || !notaFiscal.value);
});

const podeEmitirNfse = computed(() => {
  if (props.osStatus !== 'FINALIZADA') return false;
  const statusNfse = notaFiscal.value?.status_nfse ?? 'PENDENTE';
  const emitir = notaFiscal.value?.emitir_nfse ?? true;
  return emitir && (statusNfse === 'PENDENTE' || !notaFiscal.value);
});

</script>

<template>
  <div>
    <!-- Cabeçalho -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
        <LucideIcon :icon="FileText" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Nota Fiscal</h3>
    </div>

    <!-- Modo edição -->
    <template v-if="isEditing">
      <div class="flex flex-col gap-4">
        <!-- Dica -->
        <div class="flex items-start gap-3 p-3 bg-brand-primary-light border border-brand-primary/20 rounded-xl text-brand-primary text-sm">
          <Info :size="16" class="mt-0.5 shrink-0" />
          <span>
            Configure os dados fiscais da OS. Ao salvar a ordem de serviço, estas configurações
            serão salvas automaticamente junto com os demais dados.
          </span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseInput
            v-model="natureza_operacao"
            label="Natureza da Operação"
            placeholder="Ex: Prestação de Serviço"
            :maxlength="60"
          />

          <BaseSelect
            :model-value="finalidade_emissao ?? undefined"
            label="Finalidade de Emissão"
            :options="FINALIDADE_OPTIONS"
            placeholder="Selecione..."
            @update:model-value="finalidade_emissao = $event as number"
          />

          <BaseSelect
            :model-value="indicador_presenca ?? undefined"
            label="Indicador de Presença"
            :options="INDICADOR_OPTIONS"
            placeholder="Selecione..."
            @update:model-value="indicador_presenca = $event as number"
          />
        </div>

        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            v-model="consumidor_final"
            type="checkbox"
            class="w-4 h-4 rounded border-zinc-300 accent-brand-primary cursor-pointer"
          />
          <span class="text-sm text-zinc-700">Consumidor Final</span>
        </label>

        <!-- Flags de emissão -->
        <div class="flex flex-col gap-1.5 pt-2 border-t border-zinc-100">
          <p class="text-xs text-zinc-500 font-medium">Documentos a emitir</p>
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input
              v-model="emitir_nfe"
              type="checkbox"
              class="w-4 h-4 rounded border-zinc-300 accent-brand-primary cursor-pointer"
            />
            <span class="text-sm text-zinc-700">NFe/NFCe (peças)</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input
              v-model="emitir_nfse"
              type="checkbox"
              class="w-4 h-4 rounded border-zinc-300 accent-brand-primary cursor-pointer"
            />
            <span class="text-sm text-zinc-700">NFSe (mão de obra)</span>
          </label>
        </div>
      </div>
    </template>

    <!-- Modo visualização (FINALIZADA / CANCELADA) -->
    <template v-else>
      <div class="flex flex-col gap-3">
        <!-- NFe -->
        <div class="flex flex-col gap-1.5">
          <p class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">NFe — Peças</p>
          <div class="flex items-center gap-2">
            <span
              v-if="notaFiscal"
              :class="['px-2 py-0.5 text-xs font-semibold rounded-full', getBadge(notaFiscal.status_nfe).bg, getBadge(notaFiscal.status_nfe).text]"
            >
              {{ notaFiscal.status_nfe ?? 'PENDENTE' }}
            </span>
            <span v-else class="text-xs text-zinc-400 italic">Não configurada</span>
          </div>

          <template v-if="notaFiscal?.numero_nfe">
            <div class="flex items-center justify-between text-xs">
              <span class="text-zinc-500">Número / Série</span>
              <span class="font-medium text-zinc-700">{{ notaFiscal.numero_nfe }} / {{ notaFiscal.serie_nfe ?? '—' }}</span>
            </div>
          </template>

          <div v-if="notaFiscal?.chave_acesso_nfe" class="flex flex-col gap-0.5 text-xs">
            <span class="text-zinc-500">Chave de Acesso</span>
            <span class="font-mono text-zinc-600 break-all">{{ notaFiscal.chave_acesso_nfe }}</span>
          </div>

          <a
            v-if="notaFiscal?.url_danfe"
            :href="notaFiscal.url_danfe"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs text-brand-primary underline hover:opacity-80"
          >
            Visualizar DANFE
          </a>

          <p v-if="notaFiscal?.mensagem_nfe" class="text-xs text-zinc-500 italic">
            {{ notaFiscal.mensagem_nfe }}
          </p>

          <BaseButton
            v-if="podeEmitirNfe"
            variant="primary"
            size="sm"
            class="mt-1 w-full"
            :is-loading="isVerificando"
            @click="emitirOS(props.osNumero, 'nfe')"
          >
            <Send :size="14" class="mr-1.5" />
            Emitir NFe
          </BaseButton>
        </div>

        <!-- NFSe -->
        <div class="flex flex-col gap-1.5 pt-2 border-t border-zinc-100">
          <p class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">NFSe — Mão de Obra</p>
          <div class="flex items-center gap-2">
            <span
              v-if="notaFiscal"
              :class="['px-2 py-0.5 text-xs font-semibold rounded-full', getBadge(notaFiscal.status_nfse).bg, getBadge(notaFiscal.status_nfse).text]"
            >
              {{ notaFiscal.status_nfse ?? 'PENDENTE' }}
            </span>
            <span v-else class="text-xs text-zinc-400 italic">Não configurada</span>
          </div>

          <template v-if="notaFiscal?.numero_nfse">
            <div class="flex items-center justify-between text-xs">
              <span class="text-zinc-500">Número</span>
              <span class="font-medium text-zinc-700">{{ notaFiscal.numero_nfse }}</span>
            </div>
          </template>

          <a
            v-if="notaFiscal?.url_nfse"
            :href="notaFiscal.url_nfse"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs text-brand-primary underline hover:opacity-80"
          >
            Visualizar NFSe
          </a>

          <p v-if="notaFiscal?.mensagem_nfse" class="text-xs text-zinc-500 italic">
            {{ notaFiscal.mensagem_nfse }}
          </p>

          <BaseButton
            v-if="podeEmitirNfse"
            variant="primary"
            size="sm"
            class="mt-1 w-full"
            :is-loading="isVerificando"
            @click="emitirOS(props.osNumero, 'nfse')"
          >
            <Send :size="14" class="mr-1.5" />
            Emitir NFSe
          </BaseButton>
        </div>
      </div>
    </template>
  </div>

  <PendenciasFiscaisModal
    :is-open="pendenciasModalOpen"
    :pendencias="pendencias"
    titulo="Pendências Fiscais — OS"
    @close="pendenciasModalOpen = false"
  />
</template>
