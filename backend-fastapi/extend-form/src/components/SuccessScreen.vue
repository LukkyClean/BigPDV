<script setup lang="ts">
defineProps<{ numeroOs: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <div class="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-5">
      <svg class="w-10 h-10 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    </div>
    <h2 class="text-xl font-bold text-slate-700 mb-2">Checklist enviado!</h2>
    <p class="text-sm text-slate-500 max-w-xs">
      Os dados da vistoria da <strong>{{ numeroOs }}</strong> foram salvos com sucesso.
      Voce pode fechar esta pagina.
    </p>
  </div>
</template>
