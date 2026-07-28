<script setup lang="ts">
import type { CompanyPrintInfo } from '../print.types';

defineProps<{
  company: CompanyPrintInfo;
}>();
</script>

<template>
  <div class="text-center mb-1">
    <div v-if="company.logo" class="flex justify-center mb-1">
      <img
        :src="company.logo"
        alt="Logo da Empresa"
        class="max-h-14 max-w-full object-contain grayscale"
      />
    </div>
    <div class="font-bold text-sm uppercase">{{ company.nome }}</div>
    <div>{{ company.cnpj }}</div>
    <div>{{ company.enderecoLinha1 }}</div>
    <div v-if="company.enderecoLinha2">{{ company.enderecoLinha2 }}</div>
    <div>TEL: {{ company.contato }}</div>
  </div>
</template>
