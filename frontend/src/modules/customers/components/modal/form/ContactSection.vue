<script setup lang="ts">
/**
 * @component ContactSection
 * @description Form section for customer contact information (common for PF and PJ)
 */

import { Phone } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { useCustomerForm } from '@/modules/customers/composables/modal/context/useCustomerForm.context';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';

const configStore = useConfiguracoesStore();

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
  email,
  celular,
  telefone,
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
        <LucideIcon :icon="Phone" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Contato</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Email -->
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="email"
          type="email"
          label="E-mail"
          placeholder="email@exemplo.com"
          :required="configStore.exigirEmail"
          :error="submitCount > 0 ? errors.email : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Celular -->
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="celular"
          type="tel"
          label="Celular - WhatsApp"
          placeholder="(00) 00000-0000"
          mask="(##) #####-####"
          :required="configStore.exigirCelular"
          :error="submitCount > 0 ? errors.celular : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Telefone -->
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="telefone"
          type="tel"
          label="Telefone"
          placeholder="(00) 0000-0000"
          mask="(##) ####-####"
          :error="submitCount > 0 ? errors.telefone : ''"
          :disabled="disabled"
        />
      </div>
    </div>
  </section>
</template>
