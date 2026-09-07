<script setup lang="ts">
/**
 * @component DadosFiscaisSection
 * @description Seção de dados fiscais do produto (NCM, CFOP, CST etc.)
 *
 * Componente de apresentação — os campos pertencem ao form principal
 * gerenciado por useProductFormProvider. Não possui lógica própria de
 * query/mutation; dados fiscais são salvos junto com o produto.
 */

import { computed, ref, watch } from 'vue';
import { FileText, Info } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useProductForm } from '../../composables/useProductForm';
import { useAuthStore } from '@/shared/stores/auth.store';
import {
  CST_ICMS_OPTIONS,
  CSOSN_OPTIONS,
  UNIDADE_PRODUTO_OPTIONS,
  CST_IBS_CBS_OPTIONS,
  CST_PIS_COFINS_OPTIONS,
} from '@/shared/constants/fiscal.constants';

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
// Form context (injetado do pai)
// =============================================

const {
  fiscal_ncm,
  fiscal_cest,
  fiscal_cfop_padrao,
  fiscal_origem_mercadoria,
  fiscal_unidade_tributavel,
  fiscal_gtin_tributavel,
  fiscal_cst_icms,
  fiscal_csosn,
  fiscal_aliquota_icms_display,
  fiscal_reducao_base_icms_display,
  fiscal_codigo_beneficio_fiscal,
  fiscal_aliquota_pis_display,
  fiscal_aliquota_cofins_display,
  fiscal_cst_pis,
  fiscal_cst_cofins,
  fiscal_c_class_trib,
  fiscal_cst_ibs_cbs,
  fiscal_aliquota_ibs_display,
  fiscal_aliquota_cbs_display,
  fiscal_c_benef,
  codigo_barras,
  errors,
} = useProductForm();

// =============================================
// Regime tributário (CST vs CSOSN)
// =============================================

const authStore = useAuthStore();
const regimeTributario = computed(() => authStore.userData?.empresa?.regime_tributario ?? '');
const isSimplesNacional = computed(() => regimeTributario.value.includes('Simples Nacional'));
const regimeDefinido = computed(() => !!regimeTributario.value);

// =============================================
// GTIN ↔ Código de Barras
// =============================================

const usarCodigoBarrasComoGtin = ref(false);

watch(usarCodigoBarrasComoGtin, (checked) => {
  if (checked && codigo_barras.value) {
    fiscal_gtin_tributavel.value = codigo_barras.value;
  }
});

watch(codigo_barras, (newVal) => {
  if (usarCodigoBarrasComoGtin.value && newVal) {
    fiscal_gtin_tributavel.value = newVal;
  }
});

// Pré-marcar checkbox se GTIN === codigo_barras na populate
watch(fiscal_gtin_tributavel, (gtin) => {
  if (gtin && codigo_barras.value && gtin === codigo_barras.value) {
    usarCodigoBarrasComoGtin.value = true;
  }
}, { once: true });

// =============================================
// Constants
// =============================================

const ORIGEM_OPTIONS = [
  { value: '0', label: '0 - Nacional' },
  { value: '1', label: '1 - Estrangeira (importação direta)' },
  { value: '2', label: '2 - Estrangeira (adquirida no mercado interno)' },
  { value: '3', label: '3 - Nacional (> 40% de conteúdo importado)' },
  { value: '4', label: '4 - Nacional (Decreto 6.006/2006)' },
  { value: '5', label: '5 - Nacional (< 40% de conteúdo importado)' },
  { value: '6', label: '6 - Estrangeira (importação direta, sem similar)' },
  { value: '7', label: '7 - Estrangeira (mercado interno, sem similar)' },
  { value: '8', label: '8 - Nacional (produção em ZFM)' },
];

// =============================================
// Visibilidade dinâmica (alíquotas e tributos)
// =============================================

const exigeAliquotaIcms = computed(() =>
  !isSimplesNacional.value && ['00', '20'].includes(fiscal_cst_icms.value),
);
const exigeReducaoBase = computed(() =>
  !isSimplesNacional.value && fiscal_cst_icms.value === '20',
);
const exigeBeneficioFiscal = computed(() =>
  !isSimplesNacional.value && fiscal_cst_icms.value === '20',
);
const pisTributavel = computed(() => ['01', '02'].includes(fiscal_cst_pis.value));
const cofinsTributavel = computed(() => ['01', '02'].includes(fiscal_cst_cofins.value));
</script>

<template>
  <!-- Cabeçalho da seção -->
  <div class="flex items-center gap-3 mb-6">
    <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
      <LucideIcon :icon="FileText" />
    </div>
    <h3 class="text-lg font-semibold text-zinc-800">Dados Fiscais</h3>
  </div>

  <!-- Aviso: produto ainda não cadastrado (modo criação) -->
  <div
    v-if="isCreateMode"
    class="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm"
  >
    <Info :size="16" class="mt-0.5 shrink-0" />
    <span>
      Os dados fiscais do produto (NCM, CFOP, CST etc.) podem ser preenchidos após o cadastro inicial.
      Salve o produto primeiro e depois acesse a edição para preencher as informações fiscais.
    </span>
  </div>

  <!-- Formulário fiscal (modo edição) -->
  <div v-else class="space-y-5">
    <!-- Dica sobre dados fiscais -->
    <div class="flex items-start gap-3 p-3 bg-brand-primary-light border border-brand-primary/20 rounded-xl text-brand-primary text-sm">
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        Preencha os dados fiscais para a emissão de NF-e/NFC-e. Os campos <strong>NCM</strong>,
        <strong>CFOP</strong> e <strong>Origem</strong> são obrigatórios para a emissão.
      </span>
    </div>

    <!-- Aviso: regime tributário não configurado -->
    <div
      v-if="!regimeDefinido"
      class="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm"
    >
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        Configure o <strong>Regime Tributário</strong> na tela de Empresa para que o campo CST ou CSOSN
        seja exibido corretamente.
      </span>
    </div>

    <!-- Grid principal -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- NCM -->
      <BaseInput
        v-model="fiscal_ncm"
        label="NCM (8 dígitos)"
        placeholder="Ex: 85171200"
        :disabled="disabled"
        inputmode="numeric"
        :error="submitCount > 0 ? errors.fiscal_ncm : undefined"
      />

      <!-- CFOP Padrão -->
      <BaseInput
        v-model="fiscal_cfop_padrao"
        label="CFOP Padrão (4 dígitos)"
        placeholder="Ex: 5102"
        :disabled="disabled"
        inputmode="numeric"
        :error="submitCount > 0 ? errors.fiscal_cfop_padrao : undefined"
      />

      <!--
        Unidade Tributável — opcional. Vazia, o payload usa a unidade comercial
        do produto (e "UN" como último recurso). Pela contabilidade, forçar
        uTrib = uCom é a prática aceita no varejo fracionado; divergir exigiria
        `qTrib`/`vUnTrib`, que o payload não envia.
      -->
      <BaseSelect
        v-model="fiscal_unidade_tributavel"
        label="Unidade Tributável (opcional)"
        :options="UNIDADE_PRODUTO_OPTIONS"
        :disabled="disabled"
        placeholder="Selecione a unidade"
        :error="submitCount > 0 ? errors.fiscal_unidade_tributavel : undefined"
      />

      <!-- Origem da Mercadoria -->
      <BaseSelect
        v-model="fiscal_origem_mercadoria"
        label="Origem da Mercadoria"
        :options="ORIGEM_OPTIONS"
        :disabled="disabled"
        placeholder="Selecione a origem"
        :error="submitCount > 0 ? errors.fiscal_origem_mercadoria : undefined"
      />

      <!-- CST ICMS (regime Normal) -->
      <BaseSelect
        v-if="!regimeDefinido || !isSimplesNacional"
        v-model="fiscal_cst_icms"
        label="CST ICMS"
        :options="CST_ICMS_OPTIONS"
        :disabled="disabled"
        placeholder="Pesquise o CST..."
        :error="submitCount > 0 ? errors.fiscal_cst_icms : undefined"
      />

      <!-- CSOSN (Simples Nacional) -->
      <BaseSelect
        v-if="!regimeDefinido || isSimplesNacional"
        v-model="fiscal_csosn"
        label="CSOSN"
        :options="CSOSN_OPTIONS"
        :disabled="disabled"
        placeholder="Pesquise o CSOSN..."
        :error="submitCount > 0 ? errors.fiscal_csosn : undefined"
      />

      <!-- CEST -->
      <BaseInput
        v-model="fiscal_cest"
        label="CEST (7 dígitos)"
        placeholder="Ex: 2806400"
        :disabled="disabled"
        inputmode="numeric"
        :error="submitCount > 0 ? errors.fiscal_cest : undefined"
      />

      <!--
        GTIN Tributável — opcional. Vazio, o payload usa o código de barras do
        produto e, se ele não passar no checksum GS1, manda "SEM GTIN".
      -->
      <div>
        <BaseInput
          v-model="fiscal_gtin_tributavel"
          label="GTIN Tributável (opcional)"
          placeholder="Ex: 7891000000000"
          :disabled="disabled || usarCodigoBarrasComoGtin"
          inputmode="numeric"
          :error="submitCount > 0 ? errors.fiscal_gtin_tributavel : undefined"
        />
        <label v-if="codigo_barras" class="flex items-center gap-2 mt-1.5 cursor-pointer select-none">
          <input
            v-model="usarCodigoBarrasComoGtin"
            type="checkbox"
            class="w-3.5 h-3.5 rounded border-zinc-300 text-brand-primary accent-brand-primary cursor-pointer"
            :disabled="disabled"
          />
          <span class="text-xs text-zinc-500">Usar código de barras (EAN) do produto</span>
        </label>
      </div>
    </div>

    <!-- Alíquotas e Tributos (NF-e) -->
    <div class="mt-6 pt-5 border-t border-zinc-200">
      <h4 class="text-sm font-semibold text-zinc-700 mb-4">Alíquotas e Tributos</h4>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Alíquota ICMS (CST 00 ou 20, regime normal) -->
        <BaseInput
          v-if="exigeAliquotaIcms"
          v-model="fiscal_aliquota_icms_display"
          label="Alíquota ICMS (%)"
          placeholder="Ex: 18.00"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_aliquota_icms_display : undefined"
        />

        <!-- Redução de Base ICMS (CST 20) -->
        <BaseInput
          v-if="exigeReducaoBase"
          v-model="fiscal_reducao_base_icms_display"
          label="Redução Base ICMS (%)"
          placeholder="Ex: 41.12"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_reducao_base_icms_display : undefined"
        />

        <!-- Código Benefício Fiscal (CST 20) -->
        <BaseInput
          v-if="exigeBeneficioFiscal"
          v-model="fiscal_codigo_beneficio_fiscal"
          label="Cód. Benefício Fiscal"
          placeholder="Ex: SP000001"
          :disabled="disabled"
          maxlength="10"
          :error="submitCount > 0 ? errors.fiscal_codigo_beneficio_fiscal : undefined"
        />

        <!--
          CST PIS/COFINS só aparece FORA do Simples. No Simples o resolver
          ignora o que estiver gravado e força CST 49 zerado (os tributos vão
          na guia única), então pedir o campo é digitação descartada.
        -->
        <BaseSelect
          v-if="!isSimplesNacional"
          v-model="fiscal_cst_pis"
          label="CST PIS"
          :options="CST_PIS_COFINS_OPTIONS"
          :disabled="disabled"
          placeholder="Selecione o CST PIS"
          :error="submitCount > 0 ? errors.fiscal_cst_pis : undefined"
        />

        <!-- Alíquota PIS (CST 01 ou 02) -->
        <BaseInput
          v-if="!isSimplesNacional && pisTributavel"
          v-model="fiscal_aliquota_pis_display"
          label="Alíquota PIS (%)"
          placeholder="Ex: 1.65"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_aliquota_pis_display : undefined"
        />

        <!-- CST COFINS — mesma regra do CST PIS acima. -->
        <BaseSelect
          v-if="!isSimplesNacional"
          v-model="fiscal_cst_cofins"
          label="CST COFINS"
          :options="CST_PIS_COFINS_OPTIONS"
          :disabled="disabled"
          placeholder="Selecione o CST COFINS"
          :error="submitCount > 0 ? errors.fiscal_cst_cofins : undefined"
        />

        <!-- Alíquota COFINS (CST 01 ou 02) -->
        <BaseInput
          v-if="!isSimplesNacional && cofinsTributavel"
          v-model="fiscal_aliquota_cofins_display"
          label="Alíquota COFINS (%)"
          placeholder="Ex: 7.60"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_aliquota_cofins_display : undefined"
        />
      </div>
    </div>

    <!--
      Reforma Tributária (IBS/CBS) — RECOLHIDA.

      Os cinco campos existem no cadastro e NENHUM código os lê: um grep por
      ibs/cbs em app/services/ volta vazio. Enquanto a reforma não valer e o
      motor não os consumir, são cinco digitações por produto sem efeito
      nenhum na nota. Ficam disponíveis para quem quiser adiantar o
      preenchimento, mas fora do caminho.
    -->
    <details class="mt-6 pt-5 border-t border-zinc-200">
      <summary class="flex items-center gap-2 mb-4 cursor-pointer select-none list-none">
        <h4 class="text-sm font-semibold text-zinc-700">Reforma Tributária (IBS/CBS)</h4>
        <span class="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-zinc-100 text-zinc-500 rounded-full">Ainda não usado na emissão</span>
      </summary>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Classificação Tributária -->
        <BaseInput
          v-model="fiscal_c_class_trib"
          label="Classif. Tributária"
          placeholder="Ex: 01"
          :disabled="disabled"
          :error="submitCount > 0 ? errors.fiscal_c_class_trib : undefined"
        />

        <!-- CST IBS/CBS -->
        <BaseSelect
          v-model="fiscal_cst_ibs_cbs"
          label="CST IBS/CBS"
          :options="CST_IBS_CBS_OPTIONS"
          :disabled="disabled"
          placeholder="Pesquise o CST..."
          :error="submitCount > 0 ? errors.fiscal_cst_ibs_cbs : undefined"
        />

        <!-- Alíquota IBS -->
        <BaseInput
          v-model="fiscal_aliquota_ibs_display"
          label="Alíquota IBS (%)"
          placeholder="Ex: 5"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_aliquota_ibs_display : undefined"
        />

        <!-- Alíquota CBS -->
        <BaseInput
          v-model="fiscal_aliquota_cbs_display"
          label="Alíquota CBS (%)"
          placeholder="Ex: 3"
          :disabled="disabled"
          inputmode="decimal"
          :error="submitCount > 0 ? errors.fiscal_aliquota_cbs_display : undefined"
        />

        <!-- Código de Benefício Fiscal -->
        <BaseInput
          v-model="fiscal_c_benef"
          label="Cód. Benefício Fiscal"
          placeholder="Ex: BR123456"
          :disabled="disabled"
          :error="submitCount > 0 ? errors.fiscal_c_benef : undefined"
        />
      </div>
    </details>
  </div>
</template>
