<script setup lang="ts">
/**
 * @component FiscalView
 * @description Tela separada de "Emissão de Notas Fiscais".
 *
 * A v1 é NÃO-fiscal (plano Start): aqui mostramos um estado BLOQUEADO com CTA de
 * upgrade, sem expor a configuração fiscal. O formulário fiscal de verdade (séries,
 * CSC, certificado) já existe no código e entra aqui quando o módulo fiscal for
 * construído e `recursoDisponivel('nfe')` passar a ser true.
 */
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { FileText, Lock, ArrowLeft, Sparkles, Check } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { recursoDisponivel, PLANO_ATUAL } from '@/shared/config/planos';

const router = useRouter();

const nfeDisponivel = recursoDisponivel('nfe');
const upgradeSolicitado = ref(false);

const beneficios = [
  'Emissão de NF-e, NFC-e e NFS-e',
  'Certificado digital A1 e integração com a prefeitura',
  'Controle de séries e numeração',
  'Ambiente de homologação e produção',
];

function solicitarUpgrade() {
  // Por agora apenas sinaliza o interesse. Quando houver billing/planos reais,
  // este ponto abre o fluxo de upgrade.
  upgradeSolicitado.value = true;
}
</script>

<template>
  <div class="h-full flex flex-col p-6 overflow-y-auto">
    <!-- Header -->
    <div class="mb-6">
      <button
        type="button"
        class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors mb-3"
        @click="router.push('/empresa')"
      >
        <ArrowLeft :size="16" />
        Voltar para Dados da Empresa
      </button>
      <h1 class="text-2xl font-bold text-gray-800">Emissão de Notas Fiscais</h1>
      <p class="text-sm text-gray-500 mt-1">Configuração fiscal e emissão de documentos.</p>
    </div>

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

    <!-- Placeholder para quando o módulo fiscal existir (nfeDisponivel = true).
         Fica aqui apenas como âncora do próximo release. -->
    <div v-else class="flex-1 flex items-center justify-center text-gray-400">
      <div class="text-center">
        <FileText :size="40" class="mx-auto mb-3" />
        <p class="text-sm">Módulo fiscal em construção.</p>
      </div>
    </div>
  </div>
</template>
