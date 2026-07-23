<script setup lang="ts">
import type { Component } from 'vue';

defineProps<{
  label: string;
  value: string;
  icon: Component;
  /** Texto auxiliar abaixo do valor (ex: "12 vendas · 3 OS"). */
  hint?: string;
}>();
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <div class="flex items-center gap-2 mb-2">
      <div class="p-1.5 rounded-lg bg-brand-primary/10 text-brand-primary shrink-0">
        <component :is="icon" :size="16" />
      </div>
      <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{{ label }}</span>
    </div>
    <p class="text-2xl font-bold text-slate-800 tabular-nums leading-none">{{ value }}</p>
    <p v-if="hint" class="text-xs text-slate-400 mt-1.5">{{ hint }}</p>
  </div>
</template>
