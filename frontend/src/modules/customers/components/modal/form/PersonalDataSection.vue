<script setup lang="ts">
/**
 * @component PersonalDataSection
 * @description Form section for PF (individual) customer personal data
 */

import { computed } from 'vue';
import { User } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useCustomerForm } from '@/modules/customers/composables/modal/context/useCustomerForm.context';
import { GENDER_OPTIONS } from '@/modules/customers/composables/modal/constants/modal.constant';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';

const configStore = useConfiguracoesStore();

const rgColSpan = computed(() => {
  const temGenero = configStore.exibirGenero;
  const temData = configStore.exibirDataNascimento;
  if (!temGenero && !temData) return 'col-span-12';
  if (!temGenero || !temData) return 'col-span-12 md:col-span-6';
  return 'col-span-12 md:col-span-4';
});

// =============================================
// Props
// =============================================

interface Props {
  disabled?: boolean;
}

defineProps<Props>();

// =============================================
// Form Fields
// =============================================

const {
  nome,
  cpf,
  rg,
  genero,
  data_nascimento,
  errors,
  submitCount,
} = useCustomerForm();
</script>

<template>
  <section>
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="User" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Dados Pessoais</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Row 1: Nome, CPF -->
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="nome"
          label="Nome Completo"
          placeholder="Digite o nome completo"
          :required="true"
          :error="submitCount > 0 ? errors.nome : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="cpf"
          label="CPF"
          placeholder="000.000.000-00"
          mask="###.###.###-##"
          :required="configStore.exigirCpfPf"
          :error="submitCount > 0 ? errors.cpf : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 2: RG, Genero, Data Nascimento -->
      <div :class="rgColSpan">
        <BaseInput
          v-model="rg"
          label="RG"
          placeholder="00.000.000-0"
          mask="##.###.###-#"
          :required="configStore.exigirRgPf"
          :error="submitCount > 0 ? errors.rg : ''"
          :disabled="disabled"
        />
      </div>
      <div v-if="configStore.exibirGenero" class="col-span-12 md:col-span-4">
        <BaseSelect
          v-model="genero"
          label="Gênero"
          placeholder="Selecione"
          :options="GENDER_OPTIONS"
          :error="submitCount > 0 ? errors.genero : ''"
          :disabled="disabled"
        />
      </div>
      <div v-if="configStore.exibirDataNascimento" class="col-span-12 md:col-span-4">
        <BaseDateInput
          v-model="data_nascimento"
          label="Data de Nascimento"
          :error="submitCount > 0 ? errors.data_nascimento : ''"
          :disabled="disabled"
        />
      </div>
    </div>
  </section>
</template>
