<script setup lang="ts">
/**
 * @component DadosFiscaisSection
 * @description Seção de dados fiscais do serviço (LC116, CNAE, ISS etc.)
 *
 * Componente de apresentação — os campos pertencem ao form principal
 * gerenciado por useServicoFormProvider. Não possui lógica própria de
 * query/mutation; dados fiscais são salvos junto com o serviço.
 */

import { computed } from 'vue';
import { FileText, Info } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useServicoForm } from '../../composables/useServicoForm';
import { useAuthStore } from '@/shared/stores/auth.store';
import {
  CST_ICMS_OPTIONS,
  CSOSN_OPTIONS,
  UNIDADE_SERVICO_OPTIONS,
  CST_IBS_CBS_OPTIONS,
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
  fiscal_codigo_servico_lc116,
  fiscal_cnae,
  fiscal_aliquota_iss_display,
  fiscal_codigo_tributacao_municipio,
  fiscal_cfop_padrao,
  fiscal_cst_icms,
  fiscal_csosn,
  fiscal_unidade_tributavel,
  fiscal_c_class_trib,
  fiscal_cst_ibs_cbs,
  fiscal_aliquota_ibs_display,
  fiscal_aliquota_cbs_display,
  fiscal_c_benef,
  errors,
} = useServicoForm();

// =============================================
// Regime tributário (CST vs CSOSN)
// =============================================

const authStore = useAuthStore();
const regimeTributario = computed(() => authStore.userData?.empresa?.regime_tributario ?? '');
const isSimplesNacional = computed(() => regimeTributario.value.includes('Simples Nacional'));
const regimeDefinido = computed(() => !!regimeTributario.value);
</script>

<template>
  <!-- Cabeçalho da seção -->
  <div class="flex items-center gap-3 mb-6">
    <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
      <LucideIcon :icon="FileText" />
    </div>
    <h3 class="text-lg font-semibold text-zinc-800">Dados Fiscais</h3>
  </div>

  <!-- Aviso: serviço ainda não cadastrado (modo criação) -->
  <div
    v-if="isCreateMode"
    class="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm"
  >
    <Info :size="16" class="mt-0.5 shrink-0" />
    <span>
      Os dados fiscais do serviço (LC 116, CNAE, ISS etc.) podem ser preenchidos após o
      cadastro inicial. Salve o serviço primeiro e depois acesse a edição para preencher as
      informações fiscais.
    </span>
  </div>

  <!-- Formulário fiscal (modo edição) -->
  <div v-else class="space-y-5">
    <!-- Dica sobre dados fiscais -->
    <div class="flex items-start gap-3 p-3 bg-brand-primary-light border border-brand-primary/20 rounded-xl text-brand-primary text-sm">
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        Preencha os dados fiscais para a emissão de NFS-e. Os campos <strong>Código LC 116</strong>
        e <strong>CNAE</strong> são os mais importantes para a classificação tributária do serviço.
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
      <!-- Código LC 116 -->
      <BaseInput
        v-model="fiscal_codigo_servico_lc116"
        label="Código LC 116 (Item de Serviço)"
        placeholder="Ex: 14.01"
        :disabled="disabled"
        inputmode="numeric"
        mask="##.##"
        :error="submitCount > 0 ? errors.fiscal_codigo_servico_lc116 : undefined"
      />

      <!-- CNAE -->
      <BaseInput
        v-model="fiscal_cnae"
        label="CNAE (7 dígitos)"
        placeholder="Ex: 9512-6/00"
        :disabled="disabled"
        inputmode="numeric"
        mask="####-#/##"
        :error="submitCount > 0 ? errors.fiscal_cnae : undefined"
      />

      <!-- Alíquota ISS -->
      <BaseInput
        v-model="fiscal_aliquota_iss_display"
        label="Alíquota ISS (%)"
        placeholder="Ex: 5"
        :disabled="disabled"
        inputmode="decimal"
        :error="submitCount > 0 ? errors.fiscal_aliquota_iss_display : undefined"
      />

      <!-- CFOP Padrão -->
      <BaseInput
        v-model="fiscal_cfop_padrao"
        label="CFOP Padrão (4 dígitos)"
        placeholder="Ex: 5933"
        :disabled="disabled"
        inputmode="numeric"
        :error="submitCount > 0 ? errors.fiscal_cfop_padrao : undefined"
      />

      <!-- Unidade Tributável -->
      <BaseSelect
        v-model="fiscal_unidade_tributavel"
        label="Unidade Tributável"
        :options="UNIDADE_SERVICO_OPTIONS"
        :disabled="disabled"
        placeholder="Selecione a unidade"
        :error="submitCount > 0 ? errors.fiscal_unidade_tributavel : undefined"
      />

      <!-- Cód. Tributação Municipal -->
      <BaseInput
        v-model="fiscal_codigo_tributacao_municipio"
        label="Cód. Tributação Municipal"
        placeholder="Ex: 14.01"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.fiscal_codigo_tributacao_municipio : undefined"
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
    </div>

    <!-- Reforma Tributária (IBS/CBS) -->
    <div class="mt-6 pt-5 border-t border-zinc-200">
      <div class="flex items-center gap-2 mb-4">
        <h4 class="text-sm font-semibold text-zinc-700">Reforma Tributária (IBS/CBS)</h4>
        <span class="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-emerald-100 text-emerald-700 rounded-full">Novo</span>
      </div>

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
    </div>
  </div>
</template>
