<script setup lang="ts">
import { MapPin, FileText, Phone, Building2 } from 'lucide-vue-next';
import type { CompanyPrintInfo } from '../print.types';

defineProps<{
  company: CompanyPrintInfo;
  documentLabel: string;
  documentNumber: string;
  dateLabel: string;
  dateValue: string;
  finalizadaDate?: string;
}>();
</script>

<template>
  <header class="border border-slate-800 rounded-lg p-4 mb-4 flex justify-between items-start gap-4">
    <div class="flex items-start gap-4">
      <div class="w-24 h-24 bg-white border border-slate-300 rounded-lg flex items-center justify-center shrink-0 overflow-hidden">
        <img v-if="company.logo" :src="company.logo" alt="Logo da Empresa" class="w-full h-full object-contain p-1" />
        <Building2 v-else :size="32" class="text-slate-400" />
      </div>
      <div>
        <h1 class="text-xl font-black text-slate-900 uppercase tracking-tight">{{ company.nome }}</h1>
        <p class="text-[10px] uppercase font-bold text-slate-500 mb-1">{{ company.razaoSocial }}</p>
        <div class="text-xs text-slate-700 space-y-0.5 mt-2">
          <p v-if="company.endereco" class="flex items-center gap-1.5"><MapPin :size="12" /> {{ company.endereco }}</p>
          <p v-if="company.cnpj" class="flex items-center gap-1.5">
            <FileText :size="12" /> {{ company.labelDocumento || 'CNPJ' }}: {{ company.cnpj }}
          </p>
          <p class="flex items-center gap-1.5">
            <Phone :size="12" /> {{ company.contato }}<template v-if="company.email"> | {{ company.email }}</template>
          </p>
        </div>
      </div>
    </div>
    <div class="text-right min-w-37.5">
      <div class="bg-slate-900 text-white p-2 rounded-t-lg text-center">
        <p class="text-[10px] font-bold uppercase tracking-wider">{{ documentLabel }}</p>
        <p class="text-2xl font-mono font-black">{{ documentNumber }}</p>
      </div>
      <div class="border-x border-b border-slate-300 p-2 rounded-b-lg text-center bg-slate-50">
        <p class="text-[10px] font-bold text-slate-500 uppercase">{{ dateLabel }}</p>
        <p class="text-sm font-bold text-slate-800">{{ dateValue }}</p>
      </div>
      <div v-if="finalizadaDate" class="mt-2 text-center">
        <p class="text-[10px] font-bold text-slate-800 uppercase border border-slate-300 bg-slate-100 rounded px-1 py-0.5 inline-block">
          FINALIZADA EM {{ finalizadaDate }}
        </p>
      </div>
    </div>
  </header>
</template>
