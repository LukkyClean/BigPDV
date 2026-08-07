<script setup lang="ts">
defineProps<{
  leftLabel: string;
  rightLabel: string;
  rightName?: string;
}>();
</script>

<template>
  <div class="grid grid-cols-2 gap-12 mt-auto pt-8">
    <div class="text-center">
      <div class="border-t border-neutral-400 w-3/4 mx-auto pt-2"></div>
      <p class="text-[10px] font-bold text-neutral-600 uppercase">{{ leftLabel }}</p>
    </div>
    <div class="text-center">
      <div class="border-t border-neutral-400 w-3/4 mx-auto pt-2"></div>
      <p class="text-[10px] font-bold text-neutral-600 uppercase">{{ rightLabel }}</p>
      <p v-if="rightName" class="text-[8px] text-neutral-600">{{ rightName }}</p>
    </div>
  </div>
</template>
