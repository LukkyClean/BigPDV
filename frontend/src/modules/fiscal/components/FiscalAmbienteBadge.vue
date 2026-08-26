<script setup lang="ts">
import { computed } from 'vue';
import { FlaskConical, ShieldCheck } from 'lucide-vue-next';

import type { FiscalConfiguracao } from '../types/fiscal.types';

interface Props {
  configuracao: FiscalConfiguracao | undefined;
  isLoading: boolean;
}

const props = defineProps<Props>();

const isHomologacao = computed(() => props.configuracao?.ambiente === 2);

const badgeClasses = computed(() =>
  isHomologacao.value
    ? 'bg-amber-100 text-amber-700 border-amber-200'
    : 'bg-green-100 text-green-700 border-green-200',
);
</script>

<template>
  <div
    v-if="!isLoading && configuracao"
    :class="['inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border', badgeClasses]"
  >
    <FlaskConical v-if="isHomologacao" :size="14" />
    <ShieldCheck v-else :size="14" />
    {{ configuracao.ambiente_label }}
    <span v-if="configuracao.mock_ativo && isHomologacao" class="opacity-60">(mock)</span>
  </div>
</template>
