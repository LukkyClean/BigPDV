<script setup lang="ts">
/**
 * @component EnderecoSection
 * @description Form section for employee addresses (dynamic list)
 */

import { watch } from 'vue';
import { MapPin, Plus, Trash2 } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { useCepQuery } from '@/shared/composables/useCepLookup';
import { ESTADOS_BRASILEIROS } from '@/shared/constants/locations.constants';
import { ref, computed } from 'vue';

import type { EnderecoFormData } from '@/shared/types/address.types';
import type { FieldEntry } from 'vee-validate';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
  onAdd: () => void;
  onRemove: (index: number) => void;
  errors?: Record<string, string | undefined>;
}

const props = defineProps<Props>();

function fieldError(index: number, field: string): string | undefined {
  // A chave do vee-validate para arrays usa COLCHETE ("enderecos[0].cep"),
  // não ponto — ver normalizeFormPath. Com ponto o lookup dava sempre
  // undefined e o erro nunca aparecia.
  return props.errors?.[`enderecos[${index}].${field}`];
}

// =============================================
// Form Fields
// =============================================

const enderecos = defineModel<FieldEntry<EnderecoFormData>[]>({ default: [] })

// =============================================
// CEP Lookup (for first address only - simplified)
// =============================================

const activeCepIndex = ref<number | null>(null);
const activeCep = computed(() => {
  if (activeCepIndex.value === null || !enderecos.value[activeCepIndex.value]) {
    return '';
  }
  return enderecos.value[activeCepIndex.value].value.cep;
});

const cepRef = ref(activeCep.value);

// Update cepRef when activeCep changes
watch(activeCep, (newVal) => {
  cepRef.value = newVal;
});

const { data: cepData, isLoading: cepIsLoading, isError: cepIsError } = useCepQuery(cepRef);

// Watch for CEP data to auto-fill address
watch(cepData, (data) => {
  if (data && activeCepIndex.value !== null && enderecos.value[activeCepIndex.value]) {
    const endereco = enderecos.value[activeCepIndex.value];
    endereco.value.logradouro = data.logradouro || '';
    endereco.value.bairro = data.bairro || '';
    endereco.value.cidade = data.localidade || '';
    endereco.value.estado = data.uf || '';
    endereco.value.complemento = data.complemento || '';
  }
});

// Track which CEP field is being edited
function handleCepFocus(index: number) {
  activeCepIndex.value = index;
  cepRef.value = enderecos.value[index]?.value.cep || '';
}
</script>

<template>
  <section>
    <!-- Section Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600"
        >
          <LucideIcon :icon="MapPin" />
        </div>
        <h3 class="text-lg font-semibold text-zinc-800">Endereço</h3>
      </div>
      <BaseButton
        v-if="!disabled"
        type="button"
        variant="secondary"
        size="sm"
        class="flex items-center gap-1"
        :disabled="enderecos.length > 1"
        @click="onAdd"
      >
        <Plus :size="16" />
        Adicionar Endereço
      </BaseButton>
    </div>

    <!-- Address Cards -->
    <div class="space-y-6">
      <div
        v-for="(endereco, index) in enderecos"
        :key="endereco.key"
      >
        <!-- Card Header -->
        <div class="flex items-center justify-between mb-4">
          <span class="text-sm font-semibold text-zinc-600">
            Endereco {{ index + 1 }}
          </span>
          <button
            v-if="!disabled && enderecos.length > 1"
            type="button"
            class="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
            @click="onRemove(index)"
          >
            <Trash2 :size="16" />
          </button>
        </div>

        <div class="grid grid-cols-12 gap-4">
          <!-- CEP -->
          <div class="col-span-12 md:col-span-3">
            <div class="relative">
              <BaseInput
                v-model="endereco.value.cep"
                @click="handleCepFocus(index)"
                label="CEP"
                placeholder="00000-000"
                mask="#####-###"
                :disabled="disabled || (cepIsLoading && activeCepIndex === index)"
                :error="submitCount > 0 ? fieldError(index, 'cep') : ''"
              />
              <div
                v-if="cepIsLoading && activeCepIndex === index"
                class="absolute right-3 top-8"
              >
                <svg
                  class="animate-spin h-4 w-4 text-brand-primary"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
            </div>
            <p
              v-if="cepIsError && activeCepIndex === index"
              class="mt-1 text-xs text-amber-600"
            >
              CEP não encontrado
            </p>
          </div>

          <!-- Logradouro -->
          <div class="col-span-12 md:col-span-7">
            <BaseInput
              v-model="endereco.value.logradouro"
              label="Logradouro/Rua"
              placeholder="Digite o logradouro"
              :disabled="disabled"
              :error="submitCount > 0 ? fieldError(index, 'logradouro') : ''"
            />
          </div>

          <!-- Numero -->
          <div class="col-span-12 md:col-span-2">
            <BaseInput
              v-model="endereco.value.numero"
              label="Numero"
              placeholder="No"
              :disabled="disabled"
              :error="submitCount > 0 ? fieldError(index, 'numero') : ''"
            />
          </div>

          <!-- Complemento -->
          <div class="col-span-12 md:col-span-6">
            <BaseInput
              v-model="endereco.value.complemento"
              label="Complemento"
              placeholder="Apto, Sala, etc. (opcional)"
              :disabled="disabled"
            />
          </div>

          <!-- Bairro -->
          <div class="col-span-12 md:col-span-6">
            <BaseInput
              v-model="endereco.value.bairro"
              label="Bairro"
              placeholder="Digite o bairro"
              :disabled="disabled"
              :error="submitCount > 0 ? fieldError(index, 'bairro') : ''"
            />
          </div>

          <!-- Cidade -->
          <div class="col-span-12 md:col-span-8">
            <BaseInput
              v-model="endereco.value.cidade"
              label="Cidade"
              placeholder="Digite a cidade"
              :disabled="disabled"
              :error="submitCount > 0 ? fieldError(index, 'cidade') : ''"
            />
          </div>

          <!-- Estado -->
          <div class="col-span-12 md:col-span-4">
            <BaseSelect
              v-model="endereco.value.estado"
              label="Estado"
              placeholder="Selecione"
              :options="ESTADOS_BRASILEIROS"
              :disabled="disabled"
              :error="submitCount > 0 ? fieldError(index, 'estado') : ''"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>