<script setup lang="ts">
/**
 * @component NfseSection
 * @description Seção de configurações fiscais municipais (NFSe, RPS, Prefeitura)
 * Refatorado para usar inject pattern
 */

import { Shield } from 'lucide-vue-next';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { REGIME_TRIBUTACAO_ISS_OPTIONS } from '../../constants/empresa.constants';
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
  isTestingPrefeitura,
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
        Testar Conexão Prefeitura (Municipal)
      </BaseButton>
    </div>
  </section>
</template>
