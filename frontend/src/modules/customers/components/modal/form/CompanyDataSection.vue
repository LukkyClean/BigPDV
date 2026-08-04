<script setup lang="ts">
/**
 * @component CompanyDataSection
 * @description Form section for PJ (company) customer data
 */

import { Building2 } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useCustomerForm } from '@/modules/customers/composables/modal/context/useCustomerForm.context';
import { REGIME_TRIBUTARIO_OPTIONS } from '@/modules/enterprise/constants/empresa.constants';
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
  razao_social,
  nome_fantasia,
  cnpj,
  ie,
  im,
  regime_tributario,
  responsavel,
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
        <LucideIcon :icon="Building2" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Dados da Empresa</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Row 1: Razao Social, Nome Fantasia -->
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="razao_social"
          label="Razão Social"
          placeholder="Digite a razão social"
          :required="true"
          :error="submitCount > 0 ? errors.razao_social : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="nome_fantasia"
          label="Nome Fantasia"
          placeholder="Digite o nome fantasia"
          :required="true"
          :error="submitCount > 0 ? errors.nome_fantasia : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 2: CNPJ, Responsavel -->
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="cnpj"
          label="CNPJ"
          placeholder="00.000.000/0000-00"
          mask="##.###.###/####-##"
          :required="configStore.exigirCnpjPj"
          :error="submitCount > 0 ? errors.cnpj : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="responsavel"
          label="Responsável"
          placeholder="Nome do responsável"
          :error="submitCount > 0 ? errors.responsavel : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 3: IE, IM, Regime Tributario -->
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="ie"
          label="Inscrição Estadual"
          placeholder="000.000.000.000"
          :required="configStore.exigirIePj"
          :error="submitCount > 0 ? errors.ie : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="im"
          label="Inscrição Municipal"
          placeholder="000.000.000.000"
          :error="submitCount > 0 ? errors.im : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseSelect
          v-model="regime_tributario"
          label="Regime Tributário"
          :options="REGIME_TRIBUTARIO_OPTIONS"
          placeholder="Selecione o regime"
          :error="submitCount > 0 ? errors.regime_tributario : ''"
          :disabled="disabled"
        />
      </div>
    </div>
  </section>
</template>
