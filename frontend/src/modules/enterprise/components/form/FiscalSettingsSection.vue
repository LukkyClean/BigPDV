<script setup lang="ts">
/**
 * @component FiscalSettingsSection
 * @description Seção de configurações fiscais estaduais (NFe, NFCe, CSC, Sefaz)
 * Refatorado para usar inject pattern
 */

import { Settings, Shield } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { SECTION_LABELS } from '../../constants/empresa.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';
import type { FiscalSettings } from '../../types/empresa.types';

// =============================================
// Props
// =============================================

interface Props {
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

// =============================================
// Inject Context
// =============================================

const {
  fiscal_settings,
  hasCertificado,
  canEmitirProducao,
  isTestingSefaz,
  handleTestSefaz,
} = useEmpresaForm();

// =============================================
// Methods
// =============================================

function updateField<K extends keyof FiscalSettings>(field: K, value: FiscalSettings[K]) {
  fiscal_settings.value = { ...fiscal_settings.value, [field]: value };
}
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Settings"/>
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">{{ SECTION_LABELS.configuracoes }}</h3>
    </div>

    <!-- SEÇÃO ESTADUAL -->
    <div>
      <h4
        class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2"
      >
        <span class="w-2 h-2 rounded-full bg-orange-400"></span>
        Emissão Estadual (Sefaz)
      </h4>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Ambiente -->
        <div class="space-y-1.5 md:col-span-3">
          <label class="text-xs font-semibold text-gray-500 uppercase">Ambiente Sefaz</label>
          <div class="flex gap-4 mt-1">
            <label
              class="flex items-center gap-2 cursor-pointer bg-gray-50 px-3 py-1.5 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
            >
              <input
                :checked="fiscal_settings.ambiente_emissao === 2"
                type="radio"
                name="ambiente_emissao"
                :disabled="disabled"
                class="radio radio-primary radio-xs accent-brand-primary"
                @change="updateField('ambiente_emissao', 2)"
              />
              <span class="text-sm text-gray-700">Homologação (Testes)</span>
            </label>
            <div
              class="tooltip"
              :data-tip="!canEmitirProducao ? 'Configure Certificado e CSC primeiro' : ''"
            >
              <label
                class="flex items-center gap-2 cursor-pointer bg-gray-50 px-3 py-1.5 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
                :class="{ 'opacity-50 cursor-not-allowed': !canEmitirProducao }"
              >
                <input
                  :checked="fiscal_settings.ambiente_emissao === 1"
                  type="radio"
                  name="ambiente_emissao"
                  :disabled="!canEmitirProducao || disabled"
                  class="radio radio-error radio-xs accent-red-600"
                  @change="updateField('ambiente_emissao', 1)"
                />
                <span class="text-sm text-gray-700 font-bold">Produção</span>
              </label>
            </div>
          </div>
        </div>

        <!-- NFe -->
        <div class="p-4 border border-gray-100 rounded-lg bg-gray-50/50 space-y-3">
          <h4 class="font-bold text-[10px] uppercase text-gray-400 tracking-wide">
            NFe (Modelo 55)
          </h4>
          <div class="grid grid-cols-2 gap-3">
            <BaseInput
              :model-value="fiscal_settings.serie_nfe"
              label="Série"
              type="number"
              :disabled="disabled"
              @update:model-value="updateField('serie_nfe', typeof $event === 'number' ? $event : Number($event))"
            />
            <BaseInput
              :model-value="fiscal_settings.ultimo_numero_nfe"
              label="Último Nº"
              type="number"
              :disabled="disabled"
              @update:model-value="updateField('ultimo_numero_nfe', typeof $event === 'number' ? $event : Number($event))"
            />
          </div>
        </div>

        <!-- NFCe -->
        <div class="p-4 border border-gray-100 rounded-lg bg-gray-50/50 space-y-3">
          <h4 class="font-bold text-[10px] uppercase text-gray-400 tracking-wide">
            NFCe (Modelo 65)
          </h4>
          <div class="grid grid-cols-2 gap-3">
            <BaseInput
              :model-value="fiscal_settings.serie_nfce"
              label="Série"
              type="number"
              :disabled="disabled"
              @update:model-value="updateField('serie_nfce', typeof $event === 'number' ? $event : Number($event))"
            />
            <BaseInput
              :model-value="fiscal_settings.ultimo_numero_nfce"
              label="Último Nº"
              type="number"
              :disabled="disabled"
              @update:model-value="updateField('ultimo_numero_nfce', typeof $event === 'number' ? $event : Number($event))"
            />
          </div>
        </div>

        <!-- CSC -->
        <div class="p-4 border border-gray-100 rounded-lg bg-gray-50/50 space-y-3">
          <h4 class="font-bold text-[10px] uppercase text-gray-400 tracking-wide">
            CSC (Token NFCe)
          </h4>
          <div class="grid grid-cols-1 gap-3">
            <BaseInput
              :model-value="fiscal_settings.csc_id"
              label="ID Token"
              type="text"
              placeholder="ex: 000001"
              :disabled="disabled"
              @update:model-value="updateField('csc_id', $event)"
            />
            <BaseInput
              :model-value="fiscal_settings.csc_token"
              label="Código CSC"
              type="text"
              placeholder="Código Alfanumérico"
              :disabled="disabled"
              @update:model-value="updateField('csc_token', $event)"
            />
          </div>
        </div>
      </div>

      <!-- Botão de Teste (Estadual) -->
      <div class="mt-4 flex justify-end">
        <BaseButton
          type="button"
          variant="secondary"
          size="sm"
          :disabled="!hasCertificado || disabled"
          :loading="isTestingSefaz"
          @click="handleTestSefaz"
        >
          <Shield :size="16" class="mr-2 text-orange-500" />
          Testar Conexão Sefaz (Estadual)
        </BaseButton>
      </div>
    </div>
  </section>
</template>
