<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { Chart, type ChartConfiguration } from 'chart.js/auto';

const props = defineProps<{ config: ChartConfiguration }>();

const canvas = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

function render() {
  if (!canvas.value) return;
  chart?.destroy();
  chart = new Chart(canvas.value, props.config);
}

onMounted(render);
watch(() => props.config, render, { deep: true });
onBeforeUnmount(() => {
  chart?.destroy();
  chart = null;
});
</script>

<template>
  <div class="relative w-full h-full">
    <canvas ref="canvas" />
  </div>
</template>
