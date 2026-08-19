<script setup lang="ts">
/**
 * @component NotaFiscalSection
 * @description Seção de nota fiscal por venda — exibida no painel lateral do SaleModal.
 *
 * Dois modos:
 * - Edição (venda ATIVA): campos editáveis de configuração NF-e com auto-save.
 * - Visualização (venda FINALIZADA/CANCELADA): status da emissão + dados da nota.
 */

import { watch, computed, ref } from 'vue';
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';
import { z } from 'zod';
import { useDebounceFn } from '@vueuse/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query';
import { FileText, Send } from 'lucide-vue-next';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import PendenciasFiscaisModal from '@/shared/components/commons/PendenciasFiscaisModal.vue';
import { useToast } from '@/shared/composables/useToast';
import { useEmitirFiscal } from '@/shared/composables/useEmitirFiscal';
import { saleService } from '../../api.service';
import type { VendaNotaFiscalUpdate } from '../../schemas/sale.schema';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';
import { vendaNotaFiscalKeys } from '../../query.keys';

// =============================================
// Props
// =============================================

interface Props {
  vendaId: number;
  saleStatus: string;
  disabled?: boolean;
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

// =============================================
// State
// =============================================

const isEditing = computed(() => props.saleStatus === 'ATIVA');
let isHydrating = false;

// =============================================
// Schema Zod + Form (VeeValidate)
// =============================================

const vendaNotaFiscalSchema = z.object({
  natureza_operacao: z.string().max(60).nullable().optional(),
  finalidade_emissao: z.number().int().nullable().optional(),
  consumidor_final: z.boolean().default(true),
  indicador_presenca: z.number().int().nullable().optional(),
});

const { defineField, setValues } = useForm({
  validationSchema: toTypedSchema(vendaNotaFiscalSchema),
  initialValues: { consumidor_final: true },
});

const [natureza_operacao] = defineField('natureza_operacao');
const [finalidade_emissao] = defineField('finalidade_emissao');
const [consumidor_final] = defineField('consumidor_final');
const [indicador_presenca] = defineField('indicador_presenca');

// =============================================
// Query
// =============================================

const queryClient = useQueryClient();
const toast = useToast();

const { data: notaFiscal } = useQuery({
  queryKey: computed(() => vendaNotaFiscalKeys.detail(props.vendaId)),
  queryFn: () => saleService.getVendaNotaFiscal(props.vendaId),
  staleTime: 1000 * 60,
});

watch(notaFiscal, (nota) => {
  if (!nota) return;
  isHydrating = true;
  setValues({
    natureza_operacao: nota.natureza_operacao ?? '',
    finalidade_emissao: nota.finalidade_emissao ?? undefined,
    consumidor_final: nota.consumidor_final ?? true,
    indicador_presenca: nota.indicador_presenca ?? undefined,
  } as any, false);
  queueMicrotask(() => {
    isHydrating = false;
  });
}, { immediate: true });

// =============================================
// Mutation + Auto-save
// =============================================

const isSaving = ref(false);

const { mutateAsync: salvar } = useMutation({
  mutationFn: (dados: VendaNotaFiscalUpdate) =>
    saleService.upsertVendaNotaFiscal(props.vendaId, dados),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: vendaNotaFiscalKeys.detail(props.vendaId) });
  },
  onError: (err: AxiosError<ApiError>) => {
    toast.error(getErrorMessage(err));
  },
});

async function saveNow() {
  if (!isEditing.value) return;
  isSaving.value = true;
  try {
    await salvar({
      natureza_operacao: natureza_operacao.value || null,
      finalidade_emissao: finalidade_emissao.value ?? null,
      consumidor_final: consumidor_final.value,
      indicador_presenca: indicador_presenca.value ?? null,
    });
  } finally {
    isSaving.value = false;
  }
}

const debouncedSave = useDebounceFn(() => {
  if (isHydrating) return;
  void saveNow();
}, 700);

watch(
  () => [natureza_operacao.value, finalidade_emissao.value, consumidor_final.value, indicador_presenca.value],
  () => {
    if (isHydrating) return;
    debouncedSave();
  },
);

// =============================================
// Helpers
// =============================================

const statusBadge = computed(() => {
  const s = notaFiscal.value?.status_nota ?? 'PENDENTE';
  return STATUS_BADGE[s] ?? STATUS_BADGE.PENDENTE;
});

// =============================================
// Emissão Fiscal
// =============================================

const { pendencias, pendenciasModalOpen, isVerificando, emitirVenda } = useEmitirFiscal();

const podeEmitir = computed(() => {
  const statusNota = notaFiscal.value?.status_nota ?? 'PENDENTE';
  return props.saleStatus === 'FINALIZADA' && (statusNota === 'PENDENTE' || !notaFiscal.value);
});
</script>

<template>
  <div class="mt-3 border border-zinc-200 rounded-xl overflow-hidden">
    <!-- Cabeçalho -->
    <div class="flex items-center gap-2 px-4 py-3 bg-zinc-50 border-b border-zinc-200">
      <FileText :size="15" class="text-zinc-400 shrink-0" />
      <span class="text-xs font-semibold text-zinc-600 uppercase tracking-wide">Nota Fiscal</span>
      <span
        v-if="isSaving"
        class="ml-auto text-[10px] text-zinc-400 italic"
      >
        Salvando...
      </span>
    </div>

    <!-- Modo edição (ATIVA) -->
    <template v-if="isEditing">
      <div class="p-4 flex flex-col gap-3">
        <BaseInput
          v-model="natureza_operacao"
          label="Natureza da Operação"
          placeholder="Venda de Mercadoria"
          :disabled="disabled"
          :maxlength="60"
        />

        <BaseSelect
          :model-value="finalidade_emissao ?? undefined"
          label="Finalidade de Emissão"
          :options="FINALIDADE_OPTIONS"
          placeholder="Selecione..."
          :disabled="disabled"
          @update:model-value="finalidade_emissao = $event as number"
        />

        <BaseSelect
          :model-value="indicador_presenca ?? undefined"
          label="Indicador de Presença"
          :options="INDICADOR_OPTIONS"
          placeholder="Selecione..."
          :disabled="disabled"
          @update:model-value="indicador_presenca = $event as number"
        />

        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            v-model="consumidor_final"
            type="checkbox"
            class="w-4 h-4 rounded border-zinc-300 text-brand-primary accent-brand-primary cursor-pointer"
            :disabled="disabled"
          />
          <span class="text-sm text-zinc-700">Consumidor Final</span>
        </label>
      </div>
    </template>

    <!-- Modo visualização (FINALIZADA / CANCELADA) -->
    <template v-else>
      <div class="p-4 flex flex-col gap-2">
        <!-- Status badge -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-zinc-500">Status:</span>
          <span
            v-if="notaFiscal"
            :class="['px-2 py-0.5 text-xs font-semibold rounded-full', statusBadge.bg, statusBadge.text]"
          >
            {{ notaFiscal.status_nota ?? 'PENDENTE' }}
          </span>
          <span v-else class="text-xs text-zinc-400 italic">Não configurada</span>
        </div>

        <template v-if="notaFiscal">
          <!-- Número / Série -->
          <div v-if="notaFiscal.numero_nota" class="flex items-center justify-between text-xs">
            <span class="text-zinc-500">Número / Série</span>
            <span class="font-medium text-zinc-700">{{ notaFiscal.numero_nota }} / {{ notaFiscal.serie ?? '—' }}</span>
          </div>

          <!-- Chave de acesso -->
          <div v-if="notaFiscal.chave_acesso" class="flex flex-col gap-0.5 text-xs">
            <span class="text-zinc-500">Chave de Acesso</span>
            <span class="font-mono text-zinc-600 break-all">{{ notaFiscal.chave_acesso }}</span>
          </div>

          <!-- DANFE -->
          <a
            v-if="notaFiscal.url_danfe"
            :href="notaFiscal.url_danfe"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs text-brand-primary underline hover:opacity-80"
          >
            Visualizar DANFE
          </a>

          <!-- Mensagem SEFAZ (erro) -->
          <p v-if="notaFiscal.mensagem_sefaz" class="text-xs text-zinc-500 italic">
            {{ notaFiscal.mensagem_sefaz }}
          </p>
        </template>

        <!-- Botão Emitir NF-e -->
        <BaseButton
          v-if="podeEmitir"
          variant="primary"
          size="sm"
          class="mt-2 w-full"
          :is-loading="isVerificando"
          @click="emitirVenda(props.vendaId)"
        >
          <Send :size="14" class="mr-1.5" />
          Emitir NF-e
        </BaseButton>
      </div>
    </template>
  </div>

  <PendenciasFiscaisModal
    :is-open="pendenciasModalOpen"
    :pendencias="pendencias"
    titulo="Pendências Fiscais — Venda"
    @close="pendenciasModalOpen = false"
  />
</template>
