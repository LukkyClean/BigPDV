<script setup lang="ts">
import { FlaskConical } from 'lucide-vue-next';

import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';

import { useFiscalEmitirTesteMutation } from '../composables/useFiscalEmitirMutation';

interface Props {
  isOpen: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

const emitirMutation = useFiscalEmitirTesteMutation();

function handleConfirm() {
  emitirMutation.mutate(undefined, {
    onSuccess: () => emit('close'),
  });
}
</script>

<template>
  <BaseConfirmModal
    :is-open="isOpen"
    title="Emitir NF-e de Teste"
    description="Será emitida uma NF-e com dados fictícios no ambiente de homologação. Esta nota não tem valor fiscal e serve apenas para validar a integração."
    confirm-label="Emitir Teste"
    variant="warning"
    :icon="FlaskConical"
    :is-loading="emitirMutation.isPending.value"
    @close="$emit('close')"
    @confirm="handleConfirm"
  />
</template>
