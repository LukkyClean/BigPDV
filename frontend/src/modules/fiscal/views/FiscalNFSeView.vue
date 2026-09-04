<script setup lang="ts">
import { FileText } from 'lucide-vue-next';
</script>

<template>
  <div class="flex-1 flex items-start justify-center pt-16">
    <div class="text-center max-w-md">
      <div class="w-14 h-14 mx-auto rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
        <FileText :size="24" class="text-zinc-400" />
      </div>
      <h2 class="text-lg font-semibold text-zinc-700">NFS-e</h2>
      <p class="text-sm text-zinc-500 mt-2">
        A emissao de Notas Fiscais de Servico (NFS-e) sera disponibilizada em breve.
      </p>
    </div>
  </div>
</template>
