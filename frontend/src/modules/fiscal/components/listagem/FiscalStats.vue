<script setup lang="ts">
import { Clock, CheckCircle, XCircle, Ban } from 'lucide-vue-next';

import BaseStatsCard from '@/shared/components/layout/StatsCard/BaseStatsCard.vue';
import type { DocumentoFiscalResumo, DocumentoFiscalStatus } from '../../types/fiscal.types';

interface Props {
  resumo: DocumentoFiscalResumo | undefined;
  isLoading: boolean;
  activeStatus?: DocumentoFiscalStatus | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'filter-status', status: DocumentoFiscalStatus | null): void;
}>();

const cards: { status: DocumentoFiscalStatus; label: string; icon: any; key: keyof DocumentoFiscalResumo }[] = [
  { status: 'PENDENTE', label: 'Pendentes', icon: Clock, key: 'pendentes' },
  { status: 'AUTORIZADA', label: 'Autorizadas', icon: CheckCircle, key: 'autorizadas' },
  { status: 'REJEITADA', label: 'Rejeitadas', icon: XCircle, key: 'rejeitadas' },
  { status: 'CANCELADA', label: 'Canceladas', icon: Ban, key: 'canceladas' },
];

function handleClick(status: DocumentoFiscalStatus) {
  emit('filter-status', props.activeStatus === status ? null : status);
}
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 md:gap-6">
    <button
      v-for="card in cards"
      :key="card.status"
      type="button"
      class="rounded-2xl transition-all cursor-pointer focus:outline-none text-left"
      :class="[
        activeStatus === card.status
          ? 'ring-2 ring-brand-primary shadow-md scale-[1.02]'
          : 'hover:shadow-sm hover:scale-[1.01]',
      ]"
      @click="handleClick(card.status)"
    >
      <BaseStatsCard
        :icon="card.icon"
        :label="card.label"
        :value="isLoading ? '...' : String(resumo?.[card.key] ?? 0)"
      />
    </button>
  </div>
</template>
