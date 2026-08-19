<script setup lang="ts">
import { ref } from 'vue';
import { Lock, Sparkles, Check } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { recursoDisponivel, PLANO_ATUAL } from '@/shared/config/planos';

import FiscalStats from '../components/FiscalStats.vue';
import FiscalDocumentosTable from '../components/FiscalDocumentosTable.vue';
import FiscalPendenciasPanel from '../components/FiscalPendenciasPanel.vue';
import { useFiscalResumoQuery } from '../composables/useFiscalResumoQuery';

const nfeDisponivel = recursoDisponivel('nfe');
const upgradeSolicitado = ref(false);

const { data: resumo, isLoading: isResumoLoading } = useFiscalResumoQuery();

const beneficios = [
  'Emissão de NF-e, NFC-e e NFS-e',
  'Certificado digital A1 e integração com a prefeitura',
  'Controle de séries e numeração',
  'Ambiente de homologação e produção',
];

function solicitarUpgrade() {
  upgradeSolicitado.value = true;
}
</script>

<template>
  <div class="h-full flex flex-col p-6 overflow-y-auto">
    <!-- Estado bloqueado (plano Start) -->
    <div v-if="!nfeDisponivel" class="flex-1 flex items-start justify-center">
      <div class="w-full max-w-xl bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
        <div class="w-16 h-16 mx-auto rounded-2xl bg-brand-primary-light flex items-center justify-center mb-5">
          <Lock :size="28" class="text-brand-primary" />
        </div>

        <h2 class="text-xl font-bold text-gray-800">Recurso não incluído no seu plano</h2>
        <p class="text-sm text-gray-500 mt-2 leading-relaxed">
          Você está no plano <strong>{{ PLANO_ATUAL }}</strong>, que não inclui emissão de notas
          fiscais. Faça upgrade para habilitar o módulo fiscal.
        </p>

        <ul class="text-left text-sm text-gray-600 space-y-2 mt-6 mb-7">
          <li v-for="b in beneficios" :key="b" class="flex items-start gap-2">
            <Check :size="16" class="text-brand-primary shrink-0 mt-0.5" />
            <span>{{ b }}</span>
          </li>
        </ul>

        <div
          v-if="upgradeSolicitado"
          class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-700"
        >
          Interesse registrado! Em breve o módulo fiscal estará disponível — fale com o suporte
          para habilitar a emissão de notas na sua empresa.
        </div>
        <BaseButton
          v-else
          type="button"
          variant="primary"
          class="w-full justify-center py-3 text-sm font-bold"
          @click="solicitarUpgrade"
        >
          <Sparkles :size="18" class="mr-2" />
          Solicitar upgrade de plano
        </BaseButton>
      </div>
    </div>

    <!-- Centro Fiscal -->
    <div v-else class="flex flex-col gap-6 flex-1 min-h-0">
      <FiscalStats :resumo="resumo" :is-loading="isResumoLoading" />

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        <div class="lg:col-span-2">
          <FiscalDocumentosTable />
        </div>
        <div class="lg:col-span-1">
          <FiscalPendenciasPanel />
        </div>
      </div>
    </div>
  </div>
</template>
