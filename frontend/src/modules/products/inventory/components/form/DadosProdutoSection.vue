<script setup lang="ts">
/**
 * @component DadosProdutoSection
 * @description Form section for product basic data
 */

import { computed } from 'vue';
import { Package } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import ImageUploadSection from './ImageUploadSection.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useProductForm } from '../../composables/useProductForm';
import { useFornecedoresQuery } from '../../../suppliers/composables/useFornecedoresQuery';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
// Lista UNICA de unidades. Havia duas — esta, com G/ML/CM/PC, e a da unidade
// tributavel, com M2/PAR — e dava para escolher uma unidade comercial que nao
// existia na tributavel, que nasce igual a ela.
import { UNIDADE_PRODUTO_OPTIONS } from '@/shared/constants/fiscal.constants';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
}

defineProps<Props>();

// =============================================
// Constants
// =============================================


// =============================================
// Form Fields
// =============================================

const {
  nome,
  codigo_produto,
  codigo_barras,
  unidade_medida,
  categoria,
  marca,
  fornecedor_id,
  localizacao_estoque,
  observacao,
  errors,
} = useProductForm();

const { exigirCodigoBarras, exigirCategoria, unidadeMedidaPadrao } = storeToRefs(useConfiguracoesStore());

const { fornecedores } = useFornecedoresQuery();
const fornecedorOptions = computed(() => [
  { value: '', label: 'Sem fornecedor' },
  ...fornecedores.value
    .filter((f) => f.ativo)
    .map((f) => ({ value: String(f.id), label: f.nome_fantasia || f.nome })),
]);

function handleGenerateSku() {
  if (!codigo_produto.value) {
    codigo_produto.value = `PRD-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
  }
}
</script>

<template>
  <section>
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Package" />
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">Dados do Produto</h3>
    </div>

    <div class="md:flex gap-8">
      <div class="flex items-start justify-center mb-8">
        <ImageUploadSection :disabled="disabled" />
      </div>
      <div class="grid grid-cols-12 gap-4">
        <!-- Row 1: Nome, Código Produto -->

        <div class="col-span-12 md:col-span-7">
          <BaseInput
            v-model="nome"
            label="Nome do Produto"
            placeholder="Digite o nome comercial do produto"
            :required="true"
            :error="submitCount > 0 ? errors.nome : ''"
            :disabled="disabled"
          />
        </div>
        <div class="col-span-12 md:col-span-5">
          <div class="flex items-end gap-2">
            <BaseInput
            v-model="codigo_produto"
            label="Código SKU"
            placeholder="Ex: PRD-001"
            :required="true"
            :error="submitCount > 0 ? errors.codigo_produto : ''"
            :disabled="disabled"
            class="flex-1"
          >
            <template #hint>
              <span class="text-xs text-zinc-400">Identificador interno do sistema</span>
            </template>
          </BaseInput>
          <div>
          <BaseButton
            v-if="!disabled"
            variant="primary"
            :disabled="codigo_produto.length > 0"
            @click="handleGenerateSku"
          >
            Gerar
          </BaseButton>
          </div>
        </div>
        </div>
        <!-- Row 2: Código Barras, Unidade Medida, Categoria -->
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="codigo_barras"
            label="Código de Barras"
            placeholder="EAN-13 ou similar"
            :required="exigirCodigoBarras"
            :error="submitCount > 0 ? errors.codigo_barras : ''"
            :disabled="disabled"
          >
            <template v-if="!exigirCodigoBarras" #hint>
              <span class="text-xs text-zinc-400">Deixe vazio para gerar automaticamente</span>
            </template>
          </BaseInput>
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseSelect
            v-model="unidade_medida"
            label="Unidade de Medida"
            :placeholder="unidadeMedidaPadrao"
            :options="UNIDADE_PRODUTO_OPTIONS"
            :error="submitCount > 0 ? errors.unidade_medida : ''"
            :disabled="disabled"
          />
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="categoria"
            label="Categoria"
            placeholder="Ex: Bebidas, Alimentos"
            :required="exigirCategoria"
            :error="submitCount > 0 ? errors.categoria : ''"
            :disabled="disabled"
          />
        </div>

        <!-- Row 3: Marca, Fornecedor, Localização -->
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="marca"
            label="Marca"
            placeholder="Nome da marca"
            :error="submitCount > 0 ? errors.marca : ''"
            :disabled="disabled"
          />
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseSelect
            v-model="fornecedor_id"
            label="Fornecedor"
            placeholder="Selecione o fornecedor"
            :options="fornecedorOptions"
            :error="submitCount > 0 ? errors.fornecedor_id : ''"
            :disabled="disabled"
          />
        </div>
        <div class="col-span-12 md:col-span-4">
          <BaseInput
            v-model="localizacao_estoque"
            label="Localização no Estoque"
            placeholder="Ex: Corredor A, Prateleira 3"
            :error="submitCount > 0 ? errors.localizacao_estoque : ''"
            :disabled="disabled"
          />
        </div>

        <!-- Row 4: Observações -->
        <div class="col-span-12">
          <label class="block select-none text-xs font-medium text-gray-700 mb-1">
            Descrição
          </label>
          <textarea
            v-model="observacao"
            placeholder="Informações adicionais sobre o produto..."
            :disabled="disabled"
            :maxlength="500"
            rows="3"
            class="w-full px-3 py-2 border rounded-md transition-colors duration-200 outline-none text-sm placeholder:text-gray-400 text-gray-700 border-gray-300 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary resize-none"
            :class="{ 'bg-gray-100 cursor-not-allowed': disabled, 'bg-white': !disabled }"
          ></textarea>
          <div class="flex justify-between items-center mt-1">
            <p v-if="submitCount > 0 && errors.observacao" class="select-none text-xs text-red-500">
              {{ errors.observacao }}
            </p>
            <p class="text-xs text-gray-500 ml-auto">{{ observacao.length }}/500</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
