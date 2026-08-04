<script setup lang="ts">
/**
 * @component DadosFuncionarioSection
 * @description Form section for employee personal data
 */

import { computed } from 'vue';
import { User, KeyRound } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';

import { useEmployeeForm } from '../../composables/useEmployeeForm';
import { usePositionsQuery } from '../../composables/usePositionsQuery';
import {
  GENDER_OPTIONS,
  TIPO_CONTRATO_OPTIONS,
  JORNADA_TRABALHO_OPTIONS,
} from '../../constants/form.constants';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
  showUserFields?: boolean;
}

defineProps<Props>();

// =============================================
// Form Fields
// =============================================

const {
  nome,
  cpf,
  data_nascimento,
  jornada_trabalho,
  genero,
  rg,
  telefone,
  celular,
  email,
  cargo_id,
  cnh,
  salario_bruto,
  tipo_contrato,
  data_admissao,
  mae,
  pai,
  carteira_trabalho,
  usuario_nome,
  usuario_email,
  usuario_senha,
  errors,
} = useEmployeeForm();

const { data: positions, isLoading: isPositionsLoading } = usePositionsQuery();

const cargoOptions = computed(() => [
  ...(positions.value || []).map((position) => ({
    value: position.id,
    label: position.nome,
  })),
]);

const selectedCargo = computed({
  get() {
    return cargo_id.value ? String(cargo_id.value) : '';
  },
  set(value: string) {
    cargo_id.value = value ? Number(value) : null;
  },
});
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
      <h3 class="text-lg font-semibold text-zinc-800">Dados do Funcionário</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Row 1: Nome, CPF, Data Nascimento, Jornada -->
      <div class="col-span-12 md:col-span-5">
        <BaseInput
          v-model="nome"
          label="Nome Completo"
          placeholder="Digite o nome completo"
          :required="true"
          :error="submitCount > 0 ? errors.nome : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseInput
          v-model="cpf"
          label="CPF"
          placeholder="000.000.000-00"
          mask="###.###.###-##"
          :required="true"
          :error="submitCount > 0 ? errors.cpf : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-2">
        <BaseDateInput
          v-model="data_nascimento"
          label="Data Nascimento"
          :error="submitCount > 0 ? errors.data_nascimento : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-2">
        <BaseSelect
          v-model="jornada_trabalho"
          label="Jornada"
          placeholder="Selecione"
          :options="JORNADA_TRABALHO_OPTIONS"
          :error="submitCount > 0 ? errors.jornada_trabalho : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 2: Genero, RG, Telefone, Celular -->
      <div class="col-span-12 md:col-span-2">
        <BaseSelect
          v-model="genero"
          label="Genero"
          placeholder="Selecione"
          :options="GENDER_OPTIONS"
          :error="submitCount > 0 ? errors.genero : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseInput
          v-model="rg"
          label="RG"
          placeholder="Digite o RG"
          :error="submitCount > 0 ? errors.rg : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
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
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="celular"
          type="tel"
          label="Celular"
          placeholder="(00) 0.0000-0000"
          mask="(##) #.####-####"
          :error="submitCount > 0 ? errors.celular : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 3: Email, CNH, Carteira Trabalho -->
      <div class="col-span-12 md:col-span-5">
        <BaseInput
          v-model="email"
          type="email"
          label="E-mail"
          placeholder="email@exemplo.com"
          :error="submitCount > 0 ? errors.email : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseInput
          v-model="cnh"
          label="CNH"
          placeholder="Numero da CNH"
          :error="submitCount > 0 ? errors.cnh : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="carteira_trabalho"
          label="Carteira de Trabalho"
          placeholder="Numero da CTPS"
          :error="submitCount > 0 ? errors.carteira_trabalho : ''"
          :disabled="disabled"
        />
      </div>

      <!-- Row 4: Salario, Tipo Contrato, Data Admissao -->
      <div class="col-span-12 md:col-span-3">
        <MoneyInput
          v-model="salario_bruto"
          label="Salario Bruto"
          placeholder="R$ 0,00"
          :error="submitCount > 0 ? errors.salario_bruto : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseSelect
          v-model="tipo_contrato"
          label="Tipo de Contrato"
          placeholder="Selecione"
          :options="TIPO_CONTRATO_OPTIONS"
          :error="submitCount > 0 ? errors.tipo_contrato : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseDateInput
          v-model="data_admissao"
          label="Data Admissao"
          :error="submitCount > 0 ? errors.data_admissao : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-3">
        <BaseSelect
          v-model="selectedCargo"
          label="Cargo"
          placeholder="Selecione"
          :options="cargoOptions"
          :disabled="disabled || isPositionsLoading"
          :empty-message="isPositionsLoading ? 'Carregando cargos...' : undefined"
        />
      </div>

      <!-- Row 5: Mae, Pai -->
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="mae"
          label="Nome da Mae"
          placeholder="Nome completo da mae"
          :error="submitCount > 0 ? errors.mae : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-6">
        <BaseInput
          v-model="pai"
          label="Nome do Pai"
          placeholder="Nome completo do pai"
          :error="submitCount > 0 ? errors.pai : ''"
          :disabled="disabled"
        />
      </div>
    </div>

    <!-- User Access Fields (only in create mode) -->
    <template v-if="showUserFields">
      <div class="flex items-center gap-3 mt-8 mb-6">
        <div
          class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
        >
          <LucideIcon :icon="KeyRound" />
        </div>
        <h3 class="text-lg font-semibold text-zinc-800">Dados de Acesso</h3>
      </div>

      <div class="grid grid-cols-12 gap-4">
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="usuario_nome"
            label="Nome de Usuario"
            placeholder="Digite o nome do usuario"
            :required="true"
            :error="submitCount > 0 ? errors.usuario_nome : ''"
          />
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="usuario_email"
            type="email"
            label="Email de Acesso"
            placeholder="email@empresa.com"
            :required="true"
            :error="submitCount > 0 ? errors.usuario_email : ''"
          />
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="usuario_senha"
            type="password"
            label="Senha"
            placeholder="Minimo 8 caracteres"
            :required="true"
            :error="submitCount > 0 ? errors.usuario_senha : ''"
          />
        </div>
      </div>
    </template>
  </section>
</template>
