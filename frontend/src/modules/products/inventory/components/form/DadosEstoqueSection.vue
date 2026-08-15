<script setup lang="ts">
/**
 * @component DadosEstoqueSection
 * @description Form section for stock and pricing data
 */

import { computed, watch } from 'vue';
import { TrendingUp, DollarSign } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import { useProductForm } from '../../composables/useProductForm';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
  isCreateMode?: boolean;
}

defineProps<Props>();

// =============================================
// Form Fields
// =============================================

const {
  valor_varejo,
  valor_entrada,
  valor_atacado,
  quantidade,
  quantidade_minima,
  quantidade_ideal,
  errors,
} = useProductForm();

const { exigirPrecoCusto, utilizarPrecoAtacado, margemLucroPadrao } = storeToRefs(useConfiguracoesStore());

const lucro_varejo = computed(() => {
  if (valor_varejo.value > valor_entrada.value) {
    return valor_varejo.value - valor_entrada.value;
  }
  return 0;
});

const lucro_atacado = computed(() => {
  if (valor_atacado.value > valor_entrada.value) {
    return valor_atacado.value - valor_entrada.value;
  }
  return 0;
});

// Rastreia o último valor calculado automaticamente para não sobrescrever edições manuais do varejo
let ultimoVarejoAutoCalculado = 0;

watch(valor_entrada, (custo) => {
  if (margemLucroPadrao.value > 0 && custo > 0) {
    const autoValor = parseFloat((custo * (1 + margemLucroPadrao.value / 100)).toFixed(2));
    if (valor_varejo.value === 0 || valor_varejo.value === ultimoVarejoAutoCalculado) {
      valor_varejo.value = autoValor;
      ultimoVarejoAutoCalculado = autoValor;
    }
  }
});
</script>

<template>
  <section>
    <!-- Pricing Section -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="DollarSign" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Precificação</h3>
    </div>

    <div class="grid grid-cols-12 gap-4 mb-8">
      <!-- Row 1: Pricing -->
      <div class="col-span-12 md:col-span-4">
        <BaseMoneyInput
          v-model="valor_entrada"
          label="Valor de Custo"
          :required="exigirPrecoCusto"
          :error="submitCount > 0 ? errors.valor_entrada : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseMoneyInput
          v-model="valor_varejo"
          label="Valor de Varejo"
          :required="true"
          :error="submitCount > 0 ? errors.valor_varejo : ''"
          :disabled="disabled"
        />
      </div>
      <div v-if="utilizarPrecoAtacado" class="col-span-12 md:col-span-4">
        <BaseMoneyInput
          v-model="valor_atacado"
          label="Valor de Atacado"
          :error="submitCount > 0 ? errors.valor_atacado : ''"
          :disabled="disabled"
        />
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseMoneyInput
          v-model="lucro_varejo"
          label="Lucro Varejo"
          :error="submitCount > 0 ? errors.valor_entrada : ''"
          :disabled="true"
        />
      </div>
      <div v-if="utilizarPrecoAtacado" class="col-span-12 md:col-span-4">
        <BaseMoneyInput
          v-model="lucro_atacado"
          label="Lucro de Atacado"
          :error="submitCount > 0 ? errors.valor_entrada : ''"
          :disabled="true"
        />
      </div>
    </div>

    <!-- Stock Section -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="TrendingUp" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Controle de Estoque</h3>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <!-- Row 2: Stock Quantities -->
      <div v-if="isCreateMode" class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="quantidade"
          label="Quantidade Inicial"
          placeholder="0"
          type="number"
          :required="true"
          :error="submitCount > 0 ? errors.quantidade : ''"
          :disabled="disabled"
        >
          <template #hint>
            <span class="text-xs text-zinc-500">Estoque inicial do produto</span>
          </template>
        </BaseInput>
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="quantidade_minima"
          label="Quantidade Mínima"
          placeholder="0"
          type="number"
          :error="submitCount > 0 ? errors.quantidade_minima : ''"
          :disabled="disabled"
        >
          <template #hint>
            <span class="text-xs text-amber-600 font-medium">Alerta de reposição</span>
          </template>
        </BaseInput>
      </div>
      <div class="col-span-12 md:col-span-4">
        <BaseInput
          v-model="quantidade_ideal"
          label="Quantidade Ideal"
          placeholder="0"
          type="number"
          :error="submitCount > 0 ? errors.quantidade_ideal : ''"
          :disabled="disabled"
        >
          <template #hint>
            <span class="text-xs text-zinc-500">Estoque recomendado</span>
          </template>
        </BaseInput>
      </div>
    </div>

    <!-- Stock Info Card -->
    <div
      class="mt-6 p-4 bg-linear-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl"
    >
      <div class="flex items-start gap-3">
        <div
          class="w-8 h-8 bg-brand-secondary rounded-lg flex items-center justify-center text-white shrink-0 mt-0.5"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div class="flex-1">
          <h4 class="text-sm font-semibold text-brand-primary mb-1">Dica de Gestão de Estoque</h4>
          <p class="text-xs text-brand-primary leading-relaxed">
            Configure a <strong>quantidade mínima</strong> para receber alertas quando o estoque
            estiver baixo. A <strong>quantidade ideal</strong> ajuda no planejamento de compras.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
