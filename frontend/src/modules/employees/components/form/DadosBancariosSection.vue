<script setup lang="ts">
/**
 * @component DadosBancariosSection
 * @description Form section for employee banking data
 */

import { Landmark } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';

import { useEmployeeForm } from '../../composables/useEmployeeForm';
import { BANK_ACCOUNT_TYPE_OPTIONS } from '../../constants/form.constants';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
}

defineProps<Props>();

// =============================================
// Form Fields
// =============================================

const {
  titular_conta,
  tipo_conta,
  banco,
  agencia,
  conta,
  errors,
} = useEmployeeForm();
</script>

<template>
  <section>
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Landmark" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Dados Bancários</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Row 1: Titular, CPF Titular, Tipo Conta, Banco -->
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="titular_conta"
          label="Titular da Conta"
          placeholder="Nome do titular"
          :error="submitCount > 0 ? errors.titular_conta : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-2">
        <BaseSelect
          v-model="tipo_conta"
          label="Tipo da Conta"
          placeholder="Selecione"
          :options="BANK_ACCOUNT_TYPE_OPTIONS"
          :error="submitCount > 0 ? errors.tipo_conta : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseInput
          v-model="banco"
          label="Banco"
          placeholder="Nome do banco"
          :error="submitCount > 0 ? errors.banco : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 2: Agencia, Conta -->
      <div class="col-span-12 md:col-span-3">
        <BaseInput
          v-model="agencia"
          label="Agencia"
          placeholder="0000"
          :error="submitCount > 0 ? errors.agencia : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="conta"
          label="Numero da Conta"
          placeholder="00000000-0"
          :error="submitCount > 0 ? errors.conta : ''"
          :disabled="disabled"
        />
      </div>
    </div>
  </section>
</template>
