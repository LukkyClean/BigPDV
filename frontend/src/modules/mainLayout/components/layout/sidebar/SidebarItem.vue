<script setup lang="ts">
import { useRouter } from 'vue-router';

import { SidebarLabelOptions } from '@/modules/mainLayout/types/layout.types';
import type { Component } from 'vue';

defineProps<{
  id: string;
  icon: Component;
  label: SidebarLabelOptions;
  active: boolean;
}>();

const router = useRouter();

</script>
<template>
  <button
    @click="router.push({ name: id })"
    class="w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group cursor-pointer"
    :class="[
      active
        ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/15'
        : 'text-zinc-400 hover:bg-zinc-800 hover:text-white',
    ]"
  >
    <component :is="icon" :size="20" />
    <span class="font-medium text-sm">{{ label }}</span>
  </button>
</template>
