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
import { useCamposFiscaisProduto } from '@/modules/fiscal/composables/useCamposFiscaisProduto';
import { useTributacaoPadrao } from '@/modules/fiscal/composables/useTributacaoPadrao';
import {
  CST_ICMS_OPTIONS,
  CSOSN_OPTIONS,
  UNIDADE_PRODUTO_OPTIONS,
  CST_IBS_CBS_OPTIONS,
  CST_PIS_COFINS_OPTIONS,
  CST_ICMS_CALCULADOS,
  CSOSN_CALCULADOS,
  AJUDA_CAMPO_FISCAL,
} from '@/shared/constants/fiscal.constants';

// =============================================
// Props
// =============================================

interface Props {
  submitCount: number;
  disabled?: boolean;
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
// Quais campos este regime usa
// =============================================
//
// Vinha de `regime_tributario.includes('Simples Nacional')`, que errava o
// CRT 2 (Simples com excesso de sublimite usa CST) e, sem regime preenchido,
// mostrava CST e CSOSN ao mesmo tempo. Agora quem responde é o backend, pelo
// mesmo `obter_crt` que decide na hora de emitir.

const { regime, regimeConhecido, mostrar, obrigatorio } = useCamposFiscaisProduto();

// A loja já respondeu a tributação? Se respondeu, o cadastro de produto pede
// só o que é DO PRODUTO (NCM, origem, CEST, unidade) e recolhe o resto em
// "tributação específica deste produto". Se não respondeu, a tela continua
// inteira — nenhuma loja fica sem caminho por causa de configuração ausente.
const { tributacao, configurada: temTributacaoPadrao } = useTributacaoPadrao();

/** Resumo do que vai valer quando o produto não disser nada. */
const resumoDoPadrao = computed(() => {
  const t = tributacao.value;
  if (!t) return '';
  const situacao = t.csosn ? `CSOSN ${t.csosn}` : t.cst_icms ? `CST ${t.cst_icms}` : '';
  return [situacao, t.cfop_padrao ? `CFOP ${t.cfop_padrao}` : ''].filter(Boolean).join(' · ');
});

/**
 * O bloco de alíquotas some quando a loja já respondeu — MAS nunca esconde
 * valor salvo. Ocultar campo preenchido é tirar do usuário a chance de ver e
 * corrigir o que vai para a nota.
 */
const algumTributoProprio = computed(() =>
  !!(
    fiscal_cst_pis.value ||
    fiscal_cst_cofins.value ||
    fiscal_aliquota_icms_display.value ||
    fiscal_aliquota_pis_display.value ||
    fiscal_aliquota_cofins_display.value ||
    fiscal_reducao_base_icms_display.value ||
    fiscal_codigo_beneficio_fiscal.value
  ),
);
/** Algum campo do bloco ainda é do regime desta empresa? */
const blocoAliquotasTemCampo = computed(
  () =>
    mostrar('cst_pis') ||
    mostrar('cst_cofins') ||
    mostrar('aliquota_icms') ||
    mostrar('aliquota_pis') ||
    mostrar('aliquota_cofins'),
);

// No MEI/Simples o bloco inteiro desaparece: o motor grava CST 49 sozinho e
// as alíquotas não existem na nota. Sem esta conta, sobrava o título
// "Alíquotas e Tributos" com nada embaixo.
const mostrarAliquotas = computed(
  () =>
    (blocoAliquotasTemCampo.value && !temTributacaoPadrao.value) ||
    algumTributoProprio.value,
);

/**
 * A Reforma Tributária nasce FECHADA.
 *
 * Está em transição e ninguém preenche hoje — deixá-la aberta só dava cinco
 * campos a mais para o lojista não saber o que responder. Abre sozinha se o
 * produto já tiver algo gravado ali.
 */
const reformaAberta = ref(false);
watch(
  () => [
    fiscal_c_class_trib.value,
    fiscal_cst_ibs_cbs.value,
    fiscal_aliquota_ibs_display.value,
    fiscal_aliquota_cbs_display.value,
    fiscal_c_benef.value,
  ],
  (valores) => {
    if (valores.some(Boolean)) reformaAberta.value = true;
  },
  { immediate: true },
);

/** A seção de exceção começa aberta quando o produto já tem algo próprio. */
const excecaoAberta = ref(false);
watch(
  () => [fiscal_cfop_padrao.value, fiscal_csosn.value, fiscal_cst_icms.value],
  ([cfop, csosn, cst]) => {
    if (cfop || csosn || cst) excecaoAberta.value = true;
  },
  { immediate: true },
);

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
// Visibilidade que depende do VALOR de outro campo
// =============================================
//
// O mapa do servidor responde pelo regime; estas regras mudam a cada tecla e
// por isso ficam aqui. `mostrar()` continua mandando: no Simples não existe
// alíquota de ICMS, qualquer que seja o CST digitado.

const exigeAliquotaIcms = computed(
  () => mostrar('aliquota_icms') && ['00', '20'].includes(fiscal_cst_icms.value),
);
const exigeReducaoBase = computed(
  () => mostrar('reducao_base_icms') && fiscal_cst_icms.value === '20',
);
const exigeBeneficioFiscal = computed(
  () => mostrar('codigo_beneficio_fiscal') && fiscal_cst_icms.value === '20',
);
const pisTributavel = computed(
  () => mostrar('aliquota_pis') && ['01', '02'].includes(fiscal_cst_pis.value),
);
const cofinsTributavel = computed(
  () => mostrar('aliquota_cofins') && ['01', '02'].includes(fiscal_cst_cofins.value),
);

// =============================================
// Códigos que o sistema calcula × todos os códigos
// =============================================
//
// A lista completa oferecia 10 CSOSNs, e o motor calcula 3: dava para
// escolher um código que salva no cadastro e é recusado na emissão. Os
// calculados vêm primeiro e o resto fica atrás de "ver todos".

const verTodosOsCodigos = ref(false);

const opcoesCstIcms = computed(() =>
  verTodosOsCodigos.value
    ? CST_ICMS_OPTIONS
    : CST_ICMS_OPTIONS.filter((o) => CST_ICMS_CALCULADOS.includes(o.value as never)),
);

const opcoesCsosn = computed(() =>
  verTodosOsCodigos.value
    ? CSOSN_OPTIONS
    : CSOSN_OPTIONS.filter((o) => CSOSN_CALCULADOS.includes(o.value as never)),
);

/** O código já salvo pode ser um dos que o motor ainda não calcula. */
const codigoForaDoMotor = computed(() => {
  const atual = mostrar('csosn') ? fiscal_csosn.value : fiscal_cst_icms.value;
  if (!atual) return false;
  const calculados: readonly string[] = mostrar('csosn')
    ? CSOSN_CALCULADOS
    : CST_ICMS_CALCULADOS;
  return !calculados.includes(atual);
});

</script>

<template>
  <!-- Cabeçalho da seção -->
  <div class="flex items-center gap-3 mb-6">
    <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
      <LucideIcon :icon="FileText" />
    </div>
    <h3 class="text-lg font-semibold text-zinc-800">Dados Fiscais</h3>
  </div>

  <!--
    Formulário fiscal — igual no cadastro e na edição.

    Até 12/09/2026 o modo de criação mostrava só um aviso mandando salvar e
    voltar depois: o POST não aceitava o bloco fiscal. Agora aceita, na mesma
    transação, e o produto nasce pronto para emitir nota.
  -->
  <div class="space-y-5">
    <!-- Dica sobre dados fiscais -->
    <div class="flex items-start gap-3 p-3 bg-brand-primary-light border border-brand-primary/20 rounded-xl text-brand-primary text-sm">
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        Preencha os dados fiscais para a emissão de NF-e/NFC-e. Os campos <strong>NCM</strong>,
        <strong>CFOP</strong> e <strong>Origem</strong> são obrigatórios para a emissão.
      </span>
    </div>

    <!-- Regime lido do cadastro da empresa -->
    <div
      v-if="regimeConhecido"
      class="flex items-center gap-2 text-xs text-zinc-500"
    >
      <span>
        Campos exibidos para o regime <strong class="text-zinc-700">{{ regime }}</strong>,
        lido do cadastro da empresa.
      </span>
    </div>

    <!-- Código salvo que o motor ainda não calcula -->
    <div
      v-if="codigoForaDoMotor"
      class="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm"
    >
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        O código tributário deste produto ainda <strong>não é calculado</strong> pelo sistema, e a
        emissão será recusada. Os calculados hoje são
        <strong>102, 101 e 500</strong> (Simples) ou <strong>00, 20, 40, 41 e 60</strong>
        (regime normal).
      </span>
    </div>

    <!-- O que a loja já respondeu -->
    <div
      v-if="temTributacaoPadrao"
      class="flex items-start gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm"
    >
      <Info :size="16" class="mt-0.5 shrink-0" />
      <span>
        Tributação da loja: <strong>{{ resumoDoPadrao }}</strong>. Este produto segue essa regra —
        preencha abaixo só o que é dele. Um NCM com regra própria pode sobrepor.
      </span>
    </div>

    <!-- Grid principal -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- NCM -->
      <BaseInput
        v-model="fiscal_ncm"
        label="NCM"
        placeholder="Ex: 96081000"
        :required="obrigatorio('ncm')"
        :disabled="disabled"
        inputmode="numeric"
        :ajuda="AJUDA_CAMPO_FISCAL.ncm"
        :error="submitCount > 0 ? errors.fiscal_ncm : undefined"
      />

      <!-- Unidade Tributável -->
      <BaseSelect
        v-if="mostrar('unidade_tributavel')"
        v-model="fiscal_unidade_tributavel"
        label="Unidade Tributável"
        :options="UNIDADE_PRODUTO_OPTIONS"
        :required="obrigatorio('unidade_tributavel')"
        :disabled="disabled"
        placeholder="Igual à unidade de venda"
        :ajuda="AJUDA_CAMPO_FISCAL.unidade_tributavel"
        :error="submitCount > 0 ? errors.fiscal_unidade_tributavel : undefined"
      />

      <!-- Origem da Mercadoria -->
      <BaseSelect
        v-model="fiscal_origem_mercadoria"
        label="Origem da Mercadoria"
        :options="ORIGEM_OPTIONS"
        :required="obrigatorio('origem_mercadoria')"
        :disabled="disabled"
        placeholder="Selecione a origem"
        :ajuda="AJUDA_CAMPO_FISCAL.origem"
        :error="submitCount > 0 ? errors.fiscal_origem_mercadoria : undefined"
      />

      <!-- CEST -->
      <BaseInput
        v-if="mostrar('cest')"
        v-model="fiscal_cest"
        label="CEST"
        placeholder="Só para produto com ST"
        :disabled="disabled"
        inputmode="numeric"
        :ajuda="AJUDA_CAMPO_FISCAL.cest"
        :error="submitCount > 0 ? errors.fiscal_cest : undefined"
      />

      <!-- GTIN Tributável -->
      <div v-if="mostrar('gtin_tributavel')">
        <BaseInput
          v-model="fiscal_gtin_tributavel"
          label="GTIN Tributável"
          placeholder="Só se tiver código de barras real"
          :disabled="disabled || usarCodigoBarrasComoGtin"
          inputmode="numeric"
          :ajuda="AJUDA_CAMPO_FISCAL.gtin"
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

    <!-- Tributação específica: só quando este produto foge do padrão da loja -->
    <div v-if="temTributacaoPadrao" class="border border-zinc-200 rounded-xl overflow-hidden">
      <button
        type="button"
        class="w-full flex items-center justify-between px-4 py-3 bg-zinc-50 hover:bg-zinc-100 transition-colors cursor-pointer text-left"
        @click="excecaoAberta = !excecaoAberta"
      >
        <span class="text-sm font-medium text-zinc-700">
          Tributação específica deste produto
          <span class="block text-xs font-normal text-zinc-500">
            Só preencha se este produto for exceção à regra da loja
          </span>
        </span>
        <span class="text-xs text-zinc-500">{{ excecaoAberta ? 'Recolher' : 'Abrir' }}</span>
      </button>

      <div v-if="excecaoAberta" class="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <BaseInput
          v-model="fiscal_cfop_padrao"
          label="CFOP deste produto"
          placeholder="Vazio = usa o da loja"
          :disabled="disabled"
          inputmode="numeric"
          :ajuda="AJUDA_CAMPO_FISCAL.cfop"
          :error="submitCount > 0 ? errors.fiscal_cfop_padrao : undefined"
        />

        <BaseSelect
          v-if="mostrar('cst_icms')"
          v-model="fiscal_cst_icms"
          label="CST ICMS deste produto"
          :options="opcoesCstIcms"
          :disabled="disabled"
          placeholder="Vazio = usa o da loja"
          :ajuda="AJUDA_CAMPO_FISCAL.cst_icms"
          :error="submitCount > 0 ? errors.fiscal_cst_icms : undefined"
        />

        <BaseSelect
          v-if="mostrar('csosn')"
          v-model="fiscal_csosn"
          label="CSOSN deste produto"
          :options="opcoesCsosn"
          :disabled="disabled"
          placeholder="Vazio = usa o da loja"
          :ajuda="AJUDA_CAMPO_FISCAL.csosn"
          :error="submitCount > 0 ? errors.fiscal_csosn : undefined"
        />
      </div>
    </div>

    <!-- Sem tributação padrão configurada, os campos continuam na tela -->
    <div
      v-else
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <BaseInput
        v-model="fiscal_cfop_padrao"
        label="CFOP Padrão"
        placeholder="Ex: 5102"
        :required="obrigatorio('cfop_padrao')"
        :disabled="disabled"
        inputmode="numeric"
        :ajuda="AJUDA_CAMPO_FISCAL.cfop"
        :error="submitCount > 0 ? errors.fiscal_cfop_padrao : undefined"
      />

      <BaseSelect
        v-if="mostrar('cst_icms')"
        v-model="fiscal_cst_icms"
        label="CST ICMS"
        :options="opcoesCstIcms"
        :required="obrigatorio('cst_icms')"
        :disabled="disabled"
        placeholder="Como o ICMS é tratado"
        :ajuda="AJUDA_CAMPO_FISCAL.cst_icms"
        :error="submitCount > 0 ? errors.fiscal_cst_icms : undefined"
      />

      <BaseSelect
        v-if="mostrar('csosn')"
        v-model="fiscal_csosn"
        label="CSOSN"
        :options="opcoesCsosn"
        :required="obrigatorio('csosn')"
        :disabled="disabled"
        placeholder="Como o ICMS é tratado"
        :ajuda="AJUDA_CAMPO_FISCAL.csosn"
        :error="submitCount > 0 ? errors.fiscal_csosn : undefined"
      />
    </div>

    <!-- Os códigos que o motor não calcula ficam atrás deste link -->
    <button
      type="button"
      class="text-xs text-zinc-500 hover:text-brand-primary underline underline-offset-2 cursor-pointer"
      @click="verTodosOsCodigos = !verTodosOsCodigos"
    >
      {{
        verTodosOsCodigos
          ? 'Mostrar só os códigos que o sistema calcula'
          : 'Ver todos os códigos tributários'
      }}
    </button>

    <!-- Alíquotas e Tributos (NF-e) — descem da loja quando ela respondeu -->
    <div v-if="mostrarAliquotas" class="mt-6 pt-5 border-t border-zinc-200">
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
          :ajuda="AJUDA_CAMPO_FISCAL.aliquota_icms"
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
          :ajuda="AJUDA_CAMPO_FISCAL.reducao_base_icms"
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
          :ajuda="AJUDA_CAMPO_FISCAL.beneficio_fiscal"
          :error="submitCount > 0 ? errors.fiscal_codigo_beneficio_fiscal : undefined"
        />

        <!-- CST PIS -->
        <BaseSelect
          v-if="mostrar('cst_pis')"
          v-model="fiscal_cst_pis"
          label="CST PIS"
          :options="CST_PIS_COFINS_OPTIONS"
          :disabled="disabled"
          placeholder="Selecione o CST PIS"
          :ajuda="AJUDA_CAMPO_FISCAL.cst_pis"
          :error="submitCount > 0 ? errors.fiscal_cst_pis : undefined"
        />

        <!-- Alíquota PIS (CST 01 ou 02) -->
        <BaseInput
          v-if="pisTributavel"
          v-model="fiscal_aliquota_pis_display"
          label="Alíquota PIS (%)"
          placeholder="Ex: 1.65"
          :disabled="disabled"
          inputmode="decimal"
          :ajuda="AJUDA_CAMPO_FISCAL.aliquota_pis"
          :error="submitCount > 0 ? errors.fiscal_aliquota_pis_display : undefined"
        />

        <!-- CST COFINS -->
        <BaseSelect
          v-if="mostrar('cst_cofins')"
          v-model="fiscal_cst_cofins"
          label="CST COFINS"
          :options="CST_PIS_COFINS_OPTIONS"
          :disabled="disabled"
          placeholder="Selecione o CST COFINS"
          :ajuda="AJUDA_CAMPO_FISCAL.cst_cofins"
          :error="submitCount > 0 ? errors.fiscal_cst_cofins : undefined"
        />

        <!-- Alíquota COFINS (CST 01 ou 02) -->
        <BaseInput
          v-if="cofinsTributavel"
          v-model="fiscal_aliquota_cofins_display"
          label="Alíquota COFINS (%)"
          placeholder="Ex: 7.60"
          :disabled="disabled"
          inputmode="decimal"
          :ajuda="AJUDA_CAMPO_FISCAL.aliquota_cofins"
          :error="submitCount > 0 ? errors.fiscal_aliquota_cofins_display : undefined"
        />
      </div>
    </div>

    <!-- Reforma Tributária (IBS/CBS) — fechada: ninguém preenche hoje -->
    <div class="mt-6 pt-5 border-t border-zinc-200">
      <button
        type="button"
        class="w-full flex items-center justify-between gap-2 mb-4 text-left cursor-pointer"
        @click="reformaAberta = !reformaAberta"
      >
        <span class="flex items-center gap-2">
          <h4 class="text-sm font-semibold text-zinc-700">Reforma Tributária (IBS/CBS)</h4>
          <span class="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-emerald-100 text-emerald-700 rounded-full">Novo</span>
        </span>
        <span class="text-xs text-zinc-500">{{ reformaAberta ? 'Recolher' : 'Abrir' }}</span>
      </button>

      <p v-if="!reformaAberta" class="text-xs text-zinc-500">
        Em transição — preencha só se o seu contador pedir.
      </p>

      <div v-if="reformaAberta" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Classificação Tributária -->
        <BaseInput
          v-model="fiscal_c_class_trib"
          label="Classif. Tributária"
          placeholder="Ex: 01"
          :disabled="disabled"
          :ajuda="AJUDA_CAMPO_FISCAL.c_class_trib"
          :error="submitCount > 0 ? errors.fiscal_c_class_trib : undefined"
        />

        <!-- CST IBS/CBS -->
        <BaseSelect
          v-model="fiscal_cst_ibs_cbs"
          label="CST IBS/CBS"
          :options="CST_IBS_CBS_OPTIONS"
          :disabled="disabled"
          placeholder="Pesquise o CST..."
          :ajuda="AJUDA_CAMPO_FISCAL.cst_ibs_cbs"
          :error="submitCount > 0 ? errors.fiscal_cst_ibs_cbs : undefined"
        />

        <!-- Alíquota IBS -->
        <BaseInput
          v-model="fiscal_aliquota_ibs_display"
          label="Alíquota IBS (%)"
          placeholder="Ex: 5"
          :disabled="disabled"
          inputmode="decimal"
          :ajuda="AJUDA_CAMPO_FISCAL.aliquota_ibs"
          :error="submitCount > 0 ? errors.fiscal_aliquota_ibs_display : undefined"
        />

        <!-- Alíquota CBS -->
        <BaseInput
          v-model="fiscal_aliquota_cbs_display"
          label="Alíquota CBS (%)"
          placeholder="Ex: 3"
          :disabled="disabled"
          inputmode="decimal"
          :ajuda="AJUDA_CAMPO_FISCAL.aliquota_cbs"
          :error="submitCount > 0 ? errors.fiscal_aliquota_cbs_display : undefined"
        />

        <!-- Código de Benefício Fiscal -->
        <BaseInput
          v-model="fiscal_c_benef"
          label="Cód. Benefício Fiscal"
          placeholder="Ex: BR123456"
          :disabled="disabled"
          :ajuda="AJUDA_CAMPO_FISCAL.c_benef_ibs"
          :error="submitCount > 0 ? errors.fiscal_c_benef : undefined"
        />
      </div>
    </div>
  </div>
</template>
