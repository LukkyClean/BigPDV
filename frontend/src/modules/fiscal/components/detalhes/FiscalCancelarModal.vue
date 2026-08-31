<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Ban } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { useToast } from '@/shared/composables/useToast';
import { useFiscalCancelarMutation } from '../../composables/useFiscalCancelarMutation';

interface Props {
  isOpen: boolean;
  documentoIds: number[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

const justificativa = ref('');
const cancelarMutation = useFiscalCancelarMutation();
const progresso = ref(0);
const cancelando = ref(false);
const toast = useToast();

const MIN_CHARS = 15;

const isMultiplo = computed(() => props.documentoIds.length > 1);

watch(() => props.isOpen, (open) => {
  if (!open) {
    justificativa.value = '';
    progresso.value = 0;
    cancelando.value = false;
  }
});

async function handleCancelar() {
  if (props.documentoIds.length === 0 || justificativa.value.trim().length < MIN_CHARS) return;

  cancelando.value = true;
  progresso.value = 0;
  let falhas = 0;

  for (const id of props.documentoIds) {
    try {
      await cancelarMutation.mutateAsync({ id, justificativa: justificativa.value.trim() });
    } catch {
      falhas++;
    }
    progresso.value++;
  }

  if (isMultiplo.value && falhas > 0) {
    toast.warning(
      'Cancelamento parcial',
      `${falhas} de ${props.documentoIds.length} cancelamentos falharam.`,
    );
  }

  cancelando.value = false;
  emit('close');
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Cancelar Documento Fiscal"
    size="md"
    @close="!cancelando ? $emit('close') : undefined"
  >
    <div class="p-6 space-y-4">
      <div class="flex items-start gap-3 p-3 rounded-xl bg-red-50 border border-red-100">
        <Ban :size="20" class="text-red-500 shrink-0 mt-0.5" />
        <p class="text-sm text-red-700">
          <template v-if="isMultiplo">
            Você está cancelando <strong>{{ documentoIds.length }} notas fiscais</strong> autorizadas.
            Esta ação é irreversível.
          </template>
          <template v-else>
            O cancelamento é irreversível.
          </template>
          A SEFAZ exige uma justificativa com no mínimo
          <strong>{{ MIN_CHARS }} caracteres</strong>.
        </p>
      </div>

      <div>
        <label class="block text-sm font-medium text-zinc-700 mb-1.5">
          Justificativa
        </label>
        <textarea
          v-model="justificativa"
          rows="3"
          class="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none resize-none"
          placeholder="Informe o motivo do cancelamento..."
          maxlength="255"
          :disabled="cancelando"
        />
        <p class="text-xs text-zinc-400 mt-1">
          {{ justificativa.trim().length }}/{{ MIN_CHARS }} caracteres mínimos
        </p>
      </div>

      <!-- Progresso em lote -->
      <div v-if="cancelando && isMultiplo" class="flex items-center gap-2">
        <div class="flex-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-red-500 rounded-full transition-all duration-300"
            :style="{ width: (progresso / documentoIds.length * 100) + '%' }"
          />
        </div>
        <span class="text-xs text-zinc-500 tabular-nums">{{ progresso }}/{{ documentoIds.length }}</span>
      </div>

      <div class="flex justify-end gap-3 pt-2">
        <BaseButton
          type="button"
          variant="secondary"
          :disabled="cancelando"
          @click="$emit('close')"
        >
          Voltar
        </BaseButton>
        <BaseButton
          type="button"
          variant="danger"
          :disabled="justificativa.trim().length < MIN_CHARS || cancelando"
          :is-loading="cancelando"
          @click="handleCancelar"
        >
          {{ isMultiplo ? `Cancelar ${documentoIds.length} Documentos` : 'Cancelar Documento' }}
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>
