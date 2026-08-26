<script setup lang="ts">
import { ref, watch } from 'vue';
import { Ban } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { useFiscalCancelarMutation } from '../composables/useFiscalCancelarMutation';

interface Props {
  isOpen: boolean;
  documentoId: number | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

const justificativa = ref('');
const cancelarMutation = useFiscalCancelarMutation();

const MIN_CHARS = 15;

watch(() => props.isOpen, (open) => {
  if (!open) justificativa.value = '';
});

function handleCancelar() {
  if (!props.documentoId || justificativa.value.trim().length < MIN_CHARS) return;

  cancelarMutation.mutate(
    { id: props.documentoId, justificativa: justificativa.value.trim() },
    { onSuccess: () => emit('close') },
  );
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Cancelar Documento Fiscal"
    size="md"
    @close="$emit('close')"
  >
    <div class="p-6 space-y-4">
      <div class="flex items-start gap-3 p-3 rounded-xl bg-red-50 border border-red-100">
        <Ban :size="20" class="text-red-500 shrink-0 mt-0.5" />
        <p class="text-sm text-red-700">
          O cancelamento é irreversível. A SEFAZ exige uma justificativa com no mínimo
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
        />
        <p class="text-xs text-zinc-400 mt-1">
          {{ justificativa.trim().length }}/{{ MIN_CHARS }} caracteres mínimos
        </p>
      </div>

      <div class="flex justify-end gap-3 pt-2">
        <BaseButton
          type="button"
          variant="outline"
          @click="$emit('close')"
        >
          Voltar
        </BaseButton>
        <BaseButton
          type="button"
          variant="danger"
          :disabled="justificativa.trim().length < MIN_CHARS || cancelarMutation.isPending.value"
          :is-loading="cancelarMutation.isPending.value"
          @click="handleCancelar"
        >
          Cancelar Documento
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>
