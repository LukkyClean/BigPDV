<script setup lang="ts">
import { ref, watch } from 'vue';
import { Lock, Sparkles, Check } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { recursoDisponivel, PLANO_ATUAL } from '@/shared/config/planos';

import FiscalAmbienteBadge from '../components/FiscalAmbienteBadge.vue';
import { useFiscalConfiguracaoQuery } from '../composables/useFiscalConfiguracaoQuery';

const nfeDisponivel = recursoDisponivel('nfe');
const upgradeSolicitado = ref(false);

const { data: configuracao, isLoading: isConfigLoading } = useFiscalConfiguracaoQuery();

const isHomologacao = ref(true);

watch(configuracao, (cfg) => {
  if (cfg) isHomologacao.value = cfg.ambiente === 2;
}, { immediate: true });

const beneficios = [
  'Emissao de NF-e, NFC-e e NFS-e',
  'Certificado digital A1 e integracao com a prefeitura',
  'Controle de series e numeracao',
  'Ambiente de homologacao e producao',
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

        <h2 class="text-xl font-bold text-gray-800">Recurso nao incluido no seu plano</h2>
        <p class="text-sm text-gray-500 mt-2 leading-relaxed">
          Voce esta no plano <strong>{{ PLANO_ATUAL }}</strong>, que nao inclui emissao de notas
          fiscais. Faca upgrade para habilitar o modulo fiscal.
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
          Interesse registrado! Em breve o modulo fiscal estara disponivel — fale com o suporte
          para habilitar a emissao de notas na sua empresa.
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

    <!-- Centro Fiscal (layout shell) -->
    <div v-else class="flex flex-col gap-6 flex-1 min-h-0">
      <!-- Header com badge de ambiente -->
      <div class="flex items-center gap-3">
        <FiscalAmbienteBadge :configuracao="configuracao" :is-loading="isConfigLoading" />
      </div>

      <!-- Child route content -->
      <router-view :is-homologacao="isHomologacao" />
    </div>
  </div>
</template>
