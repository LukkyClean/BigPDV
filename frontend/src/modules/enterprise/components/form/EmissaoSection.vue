<script setup lang="ts">
/**
 * @component EmissaoSection
 * @description Seção unificada de configurações de emissões (Estadual e Municipal)
 * Combina FiscalSettingsSection e NfseSection em uma única seção
 */

import { Settings, Shield } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { SECTION_LABELS, REGIME_TRIBUTACAO_ISS_OPTIONS } from '../../constants/empresa.constants';
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
  isTestingPrefeitura,
  handleTestSefaz,
  handleTestPrefeitura,
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

    <!-- =============================================
         SEÇÃO ESTADUAL (NFe / NFCe / Sefaz)
         ============================================= -->
    <div class="mb-8">
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
          :is-loading="isTestingSefaz"
          @click="handleTestSefaz"
        >
          <Shield :size="16" class="mr-2 text-orange-500" />
          Testar Conexão Sefaz
        </BaseButton>
      </div>
    </div>

    <!-- Divider -->
    <div class="border-t border-gray-100 my-6"></div>

    <!-- =============================================
         SEÇÃO MUNICIPAL (NFSe / Prefeitura)
         ============================================= -->
    <div>
      <h4
        class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2"
      >
        <span class="w-2 h-2 rounded-full bg-brand-primary"></span>
        Emissão Municipal (Prefeitura)
      </h4>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- NFSe (Serviços) -->
        <div
          class="md:col-span-1 p-4 border border-brand-primary-light bg-brand-primary-light/20 rounded-lg space-y-3"
        >
          <h4 class="font-bold text-[10px] uppercase text-brand-primary tracking-wide">
            NFSe (Serviços / RPS)
          </h4>
          <div class="grid grid-cols-2 gap-3">
            <BaseInput
              :model-value="fiscal_settings.rps_serie"
              label="Série RPS"
              type="text"
              placeholder="Ex: 1"
              :disabled="disabled"
              @update:model-value="updateField('rps_serie', $event)"
            />
            <BaseInput
              :model-value="fiscal_settings.rps_ultimo_numero"
              label="Último Nº"
              type="number"
              :disabled="disabled"
              @update:model-value="updateField('rps_ultimo_numero', typeof $event === 'number' ? $event : Number($event))"
            />
          </div>
        </div>

        <!-- Integração Municipal -->
        <div class="md:col-span-2 p-5 rounded-lg border border-gray-100 bg-gray-50/30">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <BaseInput
              :model-value="fiscal_settings.prefeitura_login"
              label="Login Prefeitura"
              type="text"
              placeholder="CNPJ ou Inscrição"
              :disabled="disabled"
              @update:model-value="updateField('prefeitura_login', $event)"
            />
            <BaseInput
              :model-value="fiscal_settings.prefeitura_senha"
              label="Senha Prefeitura"
              type="password"
              placeholder="Senha do Portal ISS"
              :disabled="disabled"
              @update:model-value="updateField('prefeitura_senha', $event)"
            />
            <BaseSelect
              :model-value="fiscal_settings.regime_tributacao_iss"
              label="Regime Tributação ISS"
              :options="REGIME_TRIBUTACAO_ISS_OPTIONS"
              placeholder="Selecione..."
              :disabled="disabled"
              @update:model-value="updateField('regime_tributacao_iss', typeof $event === 'number' ? $event : Number($event))"
            />
            <BaseInput
              :model-value="fiscal_settings.prefeitura_token_api"
              label="Token / Chave API (Opcional)"
              type="text"
              placeholder="Chave de acesso via webservice"
              :disabled="disabled"
              @update:model-value="updateField('prefeitura_token_api', $event)"
            />
          </div>
        </div>
      </div>

      <!-- Botão de Teste (Municipal) -->
      <div class="mt-4 flex justify-end">
        <BaseButton
          type="button"
          variant="secondary"
          size="sm"
          :disabled="!fiscal_settings.prefeitura_login || !hasCertificado || disabled"
          :is-loading="isTestingPrefeitura"
          @click="handleTestPrefeitura"
        >
          <Shield :size="16" class="mr-2 text-brand-primary" />
          Testar Conexão Prefeitura
        </BaseButton>
      </div>
    </div>
  </section>
</template>
