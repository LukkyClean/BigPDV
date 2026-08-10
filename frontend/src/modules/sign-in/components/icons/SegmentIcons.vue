<script setup lang="ts">
/**
 * @component SegmentIcons
 * @description Renderiza ícones lucide correspondentes a cada segmento de negócio.
 */
import { computed } from 'vue';
import { Monitor, Wrench, Store, Hammer, Zap, LayoutGrid, Shirt } from 'lucide-vue-next';

const props = defineProps<{
  icon: string;
  size?: number;
}>();

const iconMap: Record<string, any> = {
  computer: Monitor,
  wrench: Wrench,
  store: Store,
  hammer: Hammer,
  bolt: Zap,
  shirt: Shirt,
  grid: LayoutGrid,
};

const resolvedIcon = computed(() => iconMap[props.icon] || LayoutGrid);
</script>

<template>
  <component :is="resolvedIcon" :size="size || 20" />
</template>
