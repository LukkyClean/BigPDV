<script setup lang="ts">
/**
 * @component EnderecoSection
 * @description Seção de endereço do formulário de empresa
 * Refatorado para usar inject pattern
 */

import { computed, ref, watch } from 'vue';
import { MapPin, Loader2 } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { SECTION_LABELS } from '../../constants/empresa.constants';
import { ESTADOS_BRASILEIROS } from '@/shared/constants/locations.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';
import { useIbgeCityLookup } from '../../composables/useIbgeCityLookup';
import { useCepQuery } from '@/shared/composables/useCepLookup';
import { unmaskCep } from '@/shared/utils/unmask.utils';

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

const { endereco_principal, errors, submitCount } = useEmpresaForm();

// =============================================
// CEP Lookup
// =============================================

const cepRef = ref<string>(unmaskCep(endereco_principal.value?.cep || ''));
const cepQuery = computed(() => {
  if (unmaskCep(endereco_principal.value?.cep || '') !== unmaskCep(cepRef.value)) return cepRef.value;
  return '';
})

const { data: cepData, isLoading: cepIsLoading, isError: cepIsError } = useCepQuery(cepQuery);

// Watch for CEP data to auto-fill address
watch(cepData, (data) => {
  if (data) {
    endereco_principal.value.cep = cepRef.value;
    endereco_principal.value.logradouro = data.logradouro || '';
    endereco_principal.value.numero = '';
    endereco_principal.value.bairro = data.bairro || '';
    endereco_principal.value.cidade = data.localidade || '';
    endereco_principal.value.estado = data.uf || '';
    endereco_principal.value.complemento = data.complemento || '';
  }
});

// =============================================
// IBGE Lookup
// =============================================

const cidadeRef = computed(() => endereco_principal.value?.cidade || '');
const ufRef = computed(() => endereco_principal.value?.estado || '');

const { codigoIbge, isLoading: isLoadingIbge } = useIbgeCityLookup(cidadeRef, ufRef);

/**
 * O campo é somente leitura e lê DAQUI — não do formulário. Nada precisa ser
 * escrito no form para o código aparecer na tela.
 *
 * Existia aqui um `watch(codigoIbge)` que copiava o resultado para dentro do
 * formulário, e ele causava um bug com cara de fantasma: a consulta ao IBGE vai
 * pela INTERNET e a resposta chega depois dos 50 ms em que o provider congela o
 * retrato usado para detectar alterações. O formulário passava a diferir do
 * retrato sem o usuário ter tocado em nada, e sair da tela pedia para salvar.
 *
 * Só na primeira visita de cada sessão porque a lista de municípios fica 24 h em
 * cache: da segunda vez o valor já está calculado na montagem e o `watch` nem
 * disparava. Daí o sintoma "só depois de instalar".
 *
 * E salvar não resolvia: `codigo_ibge` NÃO EXISTE no backend — nem coluna nem
 * schema (a palavra "ibge" não aparece no Python). O campo ia no payload e o
 * Pydantic descartava. Escrever no formulário era, portanto, sujar o estado para
 * alimentar algo que ninguém lê.
 *
 * Se um dia entrar NF-e, que precisa do código do município, o caminho é criar a
 * coluna no backend — não ressuscitar esta cópia.
 */
const codigoIbgeDisplay = computed(() => {
  return codigoIbge.value || endereco_principal.value?.codigo_ibge || '';
});
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="MapPin"/>
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">{{ SECTION_LABELS.endereco }}</h3>
    </div>

    <!-- Grid de campos -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- CEP -->
      <div class="md:col-span-1">
        <div class="relative">
          <BaseInput
            v-model="cepRef"
            label="CEP"
            placeholder="00000-000"
            mask="#####-###"
            :disabled="disabled || cepIsLoading"
          />
          <div v-if="cepIsLoading" class="absolute right-3 top-8">
            <svg class="animate-spin h-4 w-4 text-brand-primary" fill="none" viewBox="0 0 24 24">
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
        <p v-if="cepIsError" class="mt-1 text-xs text-amber-600">CEP não encontrado</p>
      </div>

      <!-- Logradouro -->
      <div class="md:col-span-2">
        <BaseInput
          v-model="endereco_principal.logradouro"
          label="Logradouro"
          type="text"
          placeholder="Rua, Avenida, etc"
          :disabled="disabled"
          :error="submitCount > 0 ? errors['endereco_principal.logradouro'] : ''"
        />
      </div>

      <!-- Número -->
      <div>
        <BaseInput
          v-model="endereco_principal.numero"
          label="Número"
          type="text"
          placeholder="123"
          :disabled="disabled"
          :error="submitCount > 0 ? errors['endereco_principal.numero'] : ''"
        />
      </div>

      <!-- Bairro -->
      <div class="md:col-span-2">
        <BaseInput
          v-model="endereco_principal.bairro"
          label="Bairro"
          type="text"
          placeholder="Nome do bairro"
          :disabled="disabled"
          :error="submitCount > 0 ? errors['endereco_principal.bairro'] : ''"
        />
      </div>

      <!-- Complemento -->
      <div class="md:col-span-2">
        <BaseInput
          v-model="endereco_principal.complemento"
          label="Complemento"
          type="text"
          placeholder="Apt, Sala (opcional)"
          :disabled="disabled"
        />
      </div>

      <!-- Cidade -->
      <div class="md:col-span-2">
        <BaseInput
          v-model="endereco_principal.cidade"
          label="Cidade"
          type="text"
          placeholder="Nome da cidade"
          :disabled="disabled"
          :error="submitCount > 0 ? errors['endereco_principal.cidade'] : ''"
        />
      </div>

      <!-- Estado (UF) -->
      <div>
        <BaseSelect
          v-model="endereco_principal.estado"
          label="Estado"
          :options="ESTADOS_BRASILEIROS"
          placeholder="UF"
          :disabled="disabled"
          :error="submitCount > 0 ? errors['endereco_principal.estado'] : ''"
        />
      </div>

      <!-- Código IBGE -->
      <div class="relative">
        <BaseInput
          :model-value="codigoIbgeDisplay"
          label="Código IBGE"
          type="text"
          readonly
          :disabled="true"
          placeholder="Automático"
        />
        <!-- Loading indicator -->
        <div v-if="isLoadingIbge" class="absolute right-3 top-8">
          <Loader2 class="w-4 h-4 animate-spin text-brand-primary" />
        </div>
      </div>
    </div>
  </section>
</template>
