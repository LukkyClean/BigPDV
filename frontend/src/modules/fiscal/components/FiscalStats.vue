<script setup lang="ts">
import { Clock, CheckCircle, XCircle, Ban } from 'lucide-vue-next';

import BaseStatsCard from '@/shared/components/layout/StatsCard/BaseStatsCard.vue';
import type { DocumentoFiscalResumo } from '../types/fiscal.types';

interface Props {
  resumo: DocumentoFiscalResumo | undefined;
  isLoading: boolean;
}

defineProps<Props>();
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <BaseStatsCard
      :icon="Clock"
      label="Pendentes"
      :value="isLoading ? '...' : String(resumo?.pendentes ?? 0)"
    />
    <BaseStatsCard
      :icon="CheckCircle"
      label="Autorizadas"
      :value="isLoading ? '...' : String(resumo?.autorizadas ?? 0)"
    />
    <BaseStatsCard
      :icon="XCircle"
      label="Rejeitadas"
      :value="isLoading ? '...' : String(resumo?.rejeitadas ?? 0)"
    />
    <BaseStatsCard
      :icon="Ban"
      label="Canceladas"
      :value="isLoading ? '...' : String(resumo?.canceladas ?? 0)"
    />
  </div>
</template>
