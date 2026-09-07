<script setup lang="ts">
/**
 * @component TaxDataSection
 * @description Seção de dados fiscais (IE, IM, Regime Tributário)
 * Refatorado para usar inject pattern
 */

import { computed } from 'vue';
import { Landmark, ShieldCheck } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { REGIME_TRIBUTARIO_OPTIONS, INDICADOR_IE_OPTIONS, NATUREZA_JURIDICA_OPTIONS, TIPO_ATIVIDADE_OPTIONS } from '../../constants/empresa.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';

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
  inscricao_estadual,
  inscricao_municipal,
  regime_tributario,
  indicador_ie,
  natureza_juridica,
  tipo_atividade,
  errors,
  submitCount,
} = useEmpresaForm();

// =============================================
// Computed & Helpers
// =============================================

const ieObrigatoria = computed(() => indicador_ie.value === '1');

function isentarIeIm() {
  indicador_ie.value = '2';
  inscricao_estadual.value = 'ISENTO';
  inscricao_municipal.value = 'ISENTO';
}
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
        >
          <LucideIcon :icon="Landmark"/>
        </div>
        <h3 class="text-lg font-semibold text-zinc-800">Dados Fiscais da PJ</h3>
      </div>

      <BaseButton
        variant="secondary"
        size="sm"
        :disabled="disabled"
        @click="isentarIeIm"
      >
        <LucideIcon :icon="ShieldCheck" class="w-4 h-4 mr-1.5" />
        Isentar IE/IM
      </BaseButton>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Indicador de IE -->
      <BaseSelect
        v-model="indicador_ie"
        label="Indicador de IE"
        :options="INDICADOR_IE_OPTIONS"
        placeholder="Selecione o indicador..."
        :required="true"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.indicador_ie : ''"
      />

      <!-- Inscrição Estadual -->
      <BaseInput
        v-model="inscricao_estadual"
        label="Inscrição Estadual (IE)"
        type="text"
        placeholder="Ex: 123.456.789.001"
        :required="ieObrigatoria"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.inscricao_estadual : ''"
      />

      <!-- Inscrição Municipal -->
      <BaseInput
        v-model="inscricao_municipal"
        label="Inscrição Municipal (IM)"
        type="text"
        placeholder="Ex: 12345678"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.inscricao_municipal : ''"
      />

      <!-- Regime Tributário -->
      <BaseSelect
        v-model="regime_tributario"
        label="Regime Tributário"
        :options="REGIME_TRIBUTARIO_OPTIONS"
        placeholder="Selecione o regime..."
        :required="true"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.regime_tributario : ''"
      />

      <!-- Natureza Jurídica -->
      <BaseSelect
        v-model="natureza_juridica"
        label="Natureza Jurídica"
        :options="NATUREZA_JURIDICA_OPTIONS"
        placeholder="Selecione a natureza..."
        :disabled="disabled"
      />

      <!-- Tipo de Atividade -->
      <BaseSelect
        v-model="tipo_atividade"
        label="Tipo de Atividade"
        :options="TIPO_ATIVIDADE_OPTIONS"
        placeholder="Selecione o tipo..."
        :disabled="disabled"
      />
    </div>
  </section>
</template>
