<script setup lang="ts">
defineProps<{
  /** Texto opcional sob o spinner (ex.: "Iniciando servidor local… 12 s"). */
  mensagem?: string | null
  detalhe?: string | null
}>()
</script>

<template>
  <div class="fixed inset-0 z-9999 flex flex-col items-center justify-center gap-4 bg-white">
    <div class="loading-spinner" />
    <div v-if="mensagem" class="text-center px-6">
      <p class="text-sm font-medium text-gray-700">{{ mensagem }}</p>
      <p v-if="detalhe" class="text-xs text-gray-400 mt-1">{{ detalhe }}</p>
    </div>
  </div>
</template>

<style scoped>
.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top-color: var(--color-brand-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
