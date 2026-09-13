<script setup lang="ts">
/**
 * @component FiscalTributacaoModal
 * @description A tributação padrão da loja — a resposta que vale para o
 * catálogo inteiro.
 *
 * POR QUE ESTA TELA EXISTE
 * ------------------------
 * CSOSN, CFOP, origem e CST de PIS/COFINS são a MESMA resposta para todos os
 * produtos da loja, e eram perguntados em cada cadastro. Aqui se responde uma
 * vez — de preferência com o contador — e o cadastro de produto volta a ser
 * nome, preço e NCM.
 *
 * A cascata continua: produto (exceção) → regra por NCM → isto.
 *
 * O botão "Sugerir para mim" usa o motor de derivação do backend, que deduz
 * pelo CRT, pela UF e pelo tipo de atividade da empresa — e explica cada
 * palpite. Sugestão com `exige_confirmacao` não entra sozinha: errar num
 * campo tributário produz nota ACEITA E ERRADA, que é pior que nota recusada.
 */

import { ref, computed, watch } from 'vue';
import { X, Scale, Info, Sparkles, CheckCircle } from 'lucide-vue-next';

import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { formatData } from '@/shared/utils/date.utils';
import {
  CST_ICMS_OPTIONS,
  CSOSN_OPTIONS,
  CST_PIS_COFINS_OPTIONS,
  CST_ICMS_CALCULADOS,
  CSOSN_CALCULADOS,
  AJUDA_CAMPO_FISCAL,
} from '@/shared/constants/fiscal.constants';
import { useTributacaoPadrao } from '../../composables/useTributacaoPadrao';
import { useCamposFiscaisProduto } from '../../composables/useCamposFiscaisProduto';
import { useSugestoesFiscais } from '../../composables/useSugestoesFiscais';

const props = defineProps<{ isOpen: boolean }>();
const emit = defineEmits<{ (e: 'update:isOpen', value: boolean): void }>();

const fechar = () => emit('update:isOpen', false);

const { tributacao, configurada, confirmadaEm, salvar, salvando } = useTributacaoPadrao();
const { regime, regimeConhecido, mostrar } = useCamposFiscaisProduto();
const { carregar, aplicarNosVazios, explicacao, veioDeSugestao, carregando } = useSugestoesFiscais();

// =============================================
// Formulário
// =============================================

const form = ref({
  cfop_padrao: '',
  origem_mercadoria: '0',
  cst_icms: '',
  csosn: '',
  cst_pis: '',
  cst_cofins: '',
  aliquota_icms: '',
  aliquota_pis: '',
  aliquota_cofins: '',
});

/** Centésimos de ponto (1800) ↔ percentual de tela ("18"). */
const paraTela = (v?: number | null) => (v === null || v === undefined ? '' : String(v / 100));
const paraBanco = (v: string) => (v === '' ? null : Math.round(Number(v) * 100));

watch(
  () => [props.isOpen, tributacao.value] as const,
  ([aberto, atual]) => {
    if (!aberto) return;
    form.value = {
      cfop_padrao: atual?.cfop_padrao ?? '',
      origem_mercadoria: atual?.origem_mercadoria != null ? String(atual.origem_mercadoria) : '0',
      cst_icms: atual?.cst_icms ?? '',
      csosn: atual?.csosn ?? '',
      cst_pis: atual?.cst_pis ?? '',
      cst_cofins: atual?.cst_cofins ?? '',
      aliquota_icms: paraTela(atual?.aliquota_icms),
      aliquota_pis: paraTela(atual?.aliquota_pis),
      aliquota_cofins: paraTela(atual?.aliquota_cofins),
    };
  },
  { immediate: true },
);

// =============================================
// Opções
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

// Só os códigos que o motor calcula: aqui não faz sentido oferecer o que a
// emissão vai recusar depois.
const opcoesCsosn = computed(() =>
  CSOSN_OPTIONS.filter((o) => (CSOSN_CALCULADOS as readonly string[]).includes(String(o.value))),
);
const opcoesCstIcms = computed(() =>
  CST_ICMS_OPTIONS.filter((o) => (CST_ICMS_CALCULADOS as readonly string[]).includes(String(o.value))),
);

// =============================================
// Sugestão do motor de derivação
// =============================================

async function sugerir() {
  await carregar();
  const aplicados = aplicarNosVazios(
    (campo) => (form.value as Record<string, unknown>)[campo] ?? '',
    (campo, valor) => {
      if (campo in form.value) {
        (form.value as Record<string, string>)[campo] = valor;
      }
    },
  );
  if (aplicados === 0) {
    // Nada a preencher não é erro: ou já estava tudo respondido, ou o que
    // falta exige confirmação e não entra sozinho.
    mensagemSugestao.value = 'Nada a sugerir: os campos vazios dependem de decisão sua.';
  } else {
    mensagemSugestao.value = `${aplicados} campo(s) preenchido(s). Confira antes de salvar.`;
  }
}

const mensagemSugestao = ref('');

// =============================================
// Salvar
// =============================================

const podeSalvar = computed(() => {
  const situacao = mostrar('csosn') ? form.value.csosn : form.value.cst_icms;
  return !!form.value.cfop_padrao && !!situacao;
});

function submeter() {
  salvar.mutate(
    {
      cfop_padrao: form.value.cfop_padrao || null,
      origem_mercadoria:
        form.value.origem_mercadoria === '' ? null : Number(form.value.origem_mercadoria),
      // Guarda só o campo do regime vigente: gravar os dois confundiria a
      // cascata se a loja trocasse de regime depois.
      cst_icms: mostrar('cst_icms') ? form.value.cst_icms || null : null,
      csosn: mostrar('csosn') ? form.value.csosn || null : null,
      cst_pis: form.value.cst_pis || null,
      cst_cofins: form.value.cst_cofins || null,
      aliquota_icms: mostrar('aliquota_icms') ? paraBanco(form.value.aliquota_icms) : null,
      aliquota_pis: mostrar('aliquota_pis') ? paraBanco(form.value.aliquota_pis) : null,
      aliquota_cofins: mostrar('aliquota_cofins') ? paraBanco(form.value.aliquota_cofins) : null,
    },
    { onSuccess: () => fechar() },
  );
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition ease-in duration-150"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        @click.self="fechar"
      >
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
          <!-- Cabeçalho -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
                <LucideIcon :icon="Scale" />
              </div>
              <div>
                <h2 class="text-lg font-bold text-zinc-900">Tributação Padrão da Loja</h2>
                <p class="text-xs text-zinc-500">
                  Responda uma vez; todo produto sem tributação própria segue esta.
                </p>
              </div>
            </div>
            <button
              type="button"
              class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
              @click="fechar"
            >
              <X :size="20" />
            </button>
          </div>

          <!-- Corpo -->
          <div class="flex-1 overflow-y-auto px-6 py-6 space-y-5">
            <div class="flex items-start gap-3 p-3 bg-brand-primary-light border border-brand-primary/20 rounded-xl text-brand-primary text-sm">
              <Info :size="16" class="mt-0.5 shrink-0" />
              <span>
                Com isto preenchido, cadastrar produto passa a ser <strong>nome, preço e NCM</strong>.
                O produto que foge da regra continua podendo ter tributação própria.
              </span>
            </div>

            <div v-if="regimeConhecido" class="text-xs text-zinc-500">
              Regime da empresa: <strong class="text-zinc-700">{{ regime }}</strong>
            </div>

            <div
              v-if="configurada && confirmadaEm"
              class="flex items-center gap-2 text-xs text-emerald-700"
            >
              <LucideIcon :icon="CheckCircle" class="w-4 h-4" />
              Confirmada em {{ formatData(confirmadaEm) }}
              <span v-if="tributacao?.confirmado_por">por {{ tributacao.confirmado_por }}</span>
            </div>

            <!-- Sugestão do motor -->
            <div class="flex flex-wrap items-center gap-3">
              <BaseButton variant="secondary" :is-loading="carregando" @click="sugerir">
                <span class="inline-flex items-center gap-2">
                  <LucideIcon :icon="Sparkles" class="w-4 h-4" />
                  Sugerir para mim
                </span>
              </BaseButton>
              <span v-if="mensagemSugestao" class="text-xs text-zinc-500">{{ mensagemSugestao }}</span>
            </div>

            <!-- Campos -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <BaseInput
                v-model="form.cfop_padrao"
                label="CFOP Padrão"
                placeholder="Ex: 5102"
                inputmode="numeric"
                :required="true"
                :ajuda="AJUDA_CAMPO_FISCAL.cfop"
              />

              <BaseSelect
                v-model="form.origem_mercadoria"
                label="Origem da Mercadoria"
                :options="ORIGEM_OPTIONS"
                :required="true"
                :ajuda="AJUDA_CAMPO_FISCAL.origem"
              />

              <BaseSelect
                v-if="mostrar('csosn')"
                v-model="form.csosn"
                label="Situação tributária (CSOSN)"
                :options="opcoesCsosn"
                placeholder="Como a loja vende no dia a dia"
                :required="true"
                :ajuda="AJUDA_CAMPO_FISCAL.csosn"
              />

              <BaseSelect
                v-if="mostrar('cst_icms')"
                v-model="form.cst_icms"
                label="Situação tributária (CST ICMS)"
                :options="opcoesCstIcms"
                placeholder="Como a loja vende no dia a dia"
                :required="true"
                :ajuda="AJUDA_CAMPO_FISCAL.cst_icms"
              />

              <BaseInput
                v-if="mostrar('aliquota_icms')"
                v-model="form.aliquota_icms"
                label="Alíquota ICMS (%)"
                placeholder="Ex: 18"
                inputmode="decimal"
                :ajuda="AJUDA_CAMPO_FISCAL.aliquota_icms"
              />

              <BaseSelect
                v-if="mostrar('cst_pis')"
                v-model="form.cst_pis"
                label="CST PIS"
                :options="CST_PIS_COFINS_OPTIONS"
                :ajuda="AJUDA_CAMPO_FISCAL.cst_pis"
              />

              <BaseSelect
                v-if="mostrar('cst_cofins')"
                v-model="form.cst_cofins"
                label="CST COFINS"
                :options="CST_PIS_COFINS_OPTIONS"
                :ajuda="AJUDA_CAMPO_FISCAL.cst_cofins"
              />

              <BaseInput
                v-if="mostrar('aliquota_pis')"
                v-model="form.aliquota_pis"
                label="Alíquota PIS (%)"
                placeholder="Ex: 1.65"
                inputmode="decimal"
                :ajuda="AJUDA_CAMPO_FISCAL.aliquota_pis"
              />

              <BaseInput
                v-if="mostrar('aliquota_cofins')"
                v-model="form.aliquota_cofins"
                label="Alíquota COFINS (%)"
                placeholder="Ex: 7.60"
                inputmode="decimal"
                :ajuda="AJUDA_CAMPO_FISCAL.aliquota_cofins"
              />
            </div>

            <p v-if="!mostrar('cst_pis')" class="text-xs text-zinc-500">
              PIS e COFINS não aparecem aqui porque, neste regime, eles vão na guia única —
              o sistema grava CST 49 sozinho na nota.
            </p>

            <p v-if="explicacao('csosn') && veioDeSugestao('csosn')" class="text-xs text-zinc-500">
              <strong>Por quê?</strong> {{ explicacao('csosn') }}
            </p>

            <div class="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm">
              <Info :size="16" class="mt-0.5 shrink-0" />
              <span>
                Estes valores vão para <strong>todas as notas</strong> dos produtos que herdam daqui.
                Confirme com seu contador antes da primeira emissão.
              </span>
            </div>
          </div>

          <!-- Rodapé -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-200 bg-zinc-50">
            <BaseButton variant="secondary" @click="fechar">Cancelar</BaseButton>
            <BaseButton
              variant="primary"
              :disabled="!podeSalvar"
              :is-loading="salvando"
              @click="submeter"
            >
              Salvar tributação padrão
            </BaseButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
