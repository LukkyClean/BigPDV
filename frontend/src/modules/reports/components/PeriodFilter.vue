<script setup lang="ts">
import { watch } from 'vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import { usePeriodo, type PeriodoPreset } from '../composables/usePeriodo';

const emit = defineEmits<{ change: [range: { inicio: string; fim: string }] }>();

const { preset, inicioCustom, fimCustom, range } = usePeriodo('mes');

const presets: { id: PeriodoPreset; label: string }[] = [
  { id: 'hoje', label: 'Hoje' },
  { id: 'ontem', label: 'Ontem' },
  { id: '7dias', label: '7 dias' },
  { id: 'mes', label: 'Mês' },
  { id: 'personalizado', label: 'Personalizado' },
];

// Emite o intervalo inicial e a cada mudança de preset/data.
watch(range, (r) => emit('change', r), { immediate: true });
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <div class="flex flex-wrap gap-1 p-1 bg-slate-100 rounded-lg">
      <button
        v-for="p in presets"
        :key="p.id"
        type="button"
        class="px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer"
        :class="preset === p.id ? 'bg-white text-brand-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'"
        @click="preset = p.id"
      >
        {{ p.label }}
      </button>
    </div>

    <div v-if="preset === 'personalizado'" class="flex items-center gap-2">
      <div class="w-40"><BaseDateInput v-model="inicioCustom" /></div>
      <span class="text-slate-400 text-sm">até</span>
      <div class="w-40"><BaseDateInput v-model="fimCustom" /></div>
    </div>
  </div>
</template>
