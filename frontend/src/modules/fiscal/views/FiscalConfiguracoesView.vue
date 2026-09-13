<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQueryClient } from '@tanstack/vue-query';
import { Shield, Building, MapPin, CheckCircle, AlertCircle, FileCheck, ArrowLeft, CalendarClock, Scale } from 'lucide-vue-next';
import { formatData } from '@/shared/utils/date.utils';
import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import FiscalCertificadoModal from '../components/configuracoes/FiscalCertificadoModal.vue';
import FiscalEmissaoEstadualModal from '../components/configuracoes/FiscalEmissaoEstadualModal.vue';
import FiscalPlataformaCard from '../components/configuracoes/FiscalPlataformaCard.vue';
import FiscalTributacaoModal from '../components/configuracoes/FiscalTributacaoModal.vue';
import { useFiscalConfiguracaoQuery } from '../composables/useFiscalConfiguracaoQuery';
import { useTributacaoPadrao } from '../composables/useTributacaoPadrao';
import { useFiscalPlataformaQuery } from '../composables/useFiscalPlataformaQuery';
import { fiscalKeys } from '../constants/fiscal.constants';

const showCertificadoModal = ref(false);
const showEstadualModal = ref(false);
const showTributacaoModal = ref(false);

// Para o cartão dizer se a loja já respondeu — sem isso o dono não sabe que
// existe uma resposta padrão, e volta a preencher produto por produto.
const { configurada: tributacaoConfigurada } = useTributacaoPadrao();

const { data: config, isLoading } = useFiscalConfiguracaoQuery();

// Mesmo número que o backend usa no gate e no painel (helpers.py): negativo é
// vencido, até 30 é aviso. Sem validade conhecida, nem um nem outro.
const certificadoVencido = computed(() => (config.value?.certificado_dias_restantes ?? 1) < 0);
const certificadoVencendo = computed(() => {
  const dias = config.value?.certificado_dias_restantes;
  return dias != null && dias >= 0 && dias <= 30;
});
const queryClient = useQueryClient();
const router = useRouter();

/**
 * Quem decide o ambiente é a PLATAFORMA, por loja — o campo daqui só arma as
 * travas locais. Enquanto o chip lia o valor local, ele podia anunciar
 * "Homologação" com a plataforma emitindo em produção: nota real saindo de um
 * teste, sem nada na tela para denunciar.
 *
 * Mesma queryKey do card de diagnóstico, então isto não gera uma segunda
 * requisição.
 */
const { data: plataforma } = useFiscalPlataformaQuery();

const ambienteVigente = computed(() =>
  plataforma.value?.consultou && plataforma.value.ambiente != null
    ? plataforma.value.ambiente
    : config.value?.ambiente,
);

/** A plataforma respondeu E discorda do que está gravado aqui. */
const ambienteDivergente = computed(() =>
  plataforma.value?.consultou === true &&
  plataforma.value.ambiente != null &&
  config.value?.ambiente != null &&
  plataforma.value.ambiente !== config.value.ambiente,
);

function openCertificadoModal() {
  showCertificadoModal.value = true;
}

function openEstadualModal() {
  showEstadualModal.value = true;
}

/**
 * O upload gravou; a tela precisa saber disso.
 *
 * O modal ja emitia `uploaded`, e ninguem escutava. Como a configuracao tem
 * `staleTime` de 30s, o card continuava dizendo "Nao configurado" depois de um
 * upload BEM-SUCEDIDO -- ate o operador sair da tela e voltar. Foi o que fez
 * parecer que o certificado nao tinha sido salvo.
 */
function aoEnviarCertificado() {
  queryClient.invalidateQueries({ queryKey: fiscalKeys.configuracao() });
}
</script>

<template>
  <div class="space-y-6">
    <!-- Daqui nao havia caminho de volta: quem chega pelo card da tela de
         Empresa so saia pelo menu lateral. -->
    <button
      type="button"
      class="inline-flex items-center gap-1.5 text-xs font-semibold text-zinc-500 hover:text-brand-primary transition-colors"
      @click="router.push('/empresa')"
    >
      <LucideIcon :icon="ArrowLeft" class="w-3.5 h-3.5" />
      Dados da Empresa
    </button>

    <!-- Page Header (padrão do sistema) -->
    <div class="flex flex-col flex-wrap sm:flex-row sm:justify-between sm:items-end gap-4">
      <PageReview
        title="Centro Fiscal"
        description="Gerencie seu certificado digital e configurações de emissão estadual e municipal."
        :is-loading="isLoading"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 1. Certificado A1 -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
                <LucideIcon :icon="Shield" />
              </div>
              <div>
                <h3 class="text-base font-bold text-zinc-900">Certificado Digital A1</h3>
                <p class="text-xs text-zinc-500">Autenticação com a SEFAZ via Focus NFe</p>
              </div>
            </div>
            <!-- Vencido / vencendo vem ANTES de "Conectado": um certificado
                 vencido continua "conectado" na emissora e não emite nada. -->
            <span
              v-if="config?.certificado_configurado && certificadoVencido"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200"
              data-chip-certificado="vencido"
            >
              <LucideIcon :icon="AlertCircle" class="w-3.5 h-3.5" />
              Vencido
            </span>
            <span
              v-else-if="config?.certificado_configurado && certificadoVencendo"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"
              data-chip-certificado="vencendo"
            >
              <LucideIcon :icon="AlertCircle" class="w-3.5 h-3.5" />
              Vence em {{ config?.certificado_dias_restantes }} dia{{ config?.certificado_dias_restantes === 1 ? '' : 's' }}
            </span>
            <span
              v-else-if="config?.certificado_configurado"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
            >
              <LucideIcon :icon="CheckCircle" class="w-3.5 h-3.5" />
              Conectado
            </span>
            <!-- Terceiro estado: o arquivo foi conferido AQUI e nao chegou na
                 emissora. Antes isso aparecia como "Conectado", e o lojista so
                 descobria na primeira emissao recusada. -->
            <span
              v-else-if="config?.certificado_status === 'VALIDADO_LOCAL'"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"
            >
              <LucideIcon :icon="AlertCircle" class="w-3.5 h-3.5" />
              Validado, não enviado
            </span>
            <span
              v-else
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"
            >
              <LucideIcon :icon="AlertCircle" class="w-3.5 h-3.5" />
              Não configurado
            </span>
          </div>

          <p class="text-sm text-zinc-600 mb-6 leading-relaxed">
            Faça o upload do seu certificado digital A1 (.pfx) para autenticar transmissões na SEFAZ. O certificado é transmitido diretamente para a nuvem de emissão com segurança.
          </p>

          <div
            v-if="config?.certificado_status === 'VALIDADO_LOCAL'"
            class="mb-6 p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 leading-relaxed"
          >
            O certificado foi conferido neste computador (senha e validade estão certas),
            mas <strong>ainda não chegou à emissora</strong> — a plataforma de emissão
            ainda não recebe certificado. Enquanto isso, a emissão não vai funcionar.
            Fale com o suporte.
          </div>

          <div
            v-if="certificadoVencido || certificadoVencendo"
            :class="[
              'mb-6 p-3 rounded-xl border text-xs leading-relaxed',
              certificadoVencido ? 'bg-red-50 border-red-200 text-red-800' : 'bg-amber-50 border-amber-200 text-amber-800',
            ]"
          >
            <template v-if="certificadoVencido">
              O certificado <strong>venceu em {{ formatData(config?.certificado_validade) }}</strong>.
              A SEFAZ recusa toda emissão até um novo ser enviado — renove com a
              certificadora e faça o upload aqui.
            </template>
            <template v-else>
              O certificado <strong>vence em {{ formatData(config?.certificado_validade) }}</strong>.
              Renove com a certificadora antes disso e envie o novo por aqui; a
              emissão para no dia do vencimento.
            </template>
          </div>

          <div v-if="config?.certificado_cnpj || config?.certificado_validade" class="mb-6 p-3 rounded-xl bg-zinc-50 border border-zinc-100 text-xs text-zinc-600 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span v-if="config?.certificado_cnpj" class="inline-flex items-center gap-2">
              <LucideIcon :icon="FileCheck" class="w-4 h-4 text-brand-primary shrink-0" />
              CNPJ Vinculado: <strong>{{ config.certificado_cnpj }}</strong>
            </span>
            <span v-if="config?.certificado_validade" class="inline-flex items-center gap-2">
              <LucideIcon :icon="CalendarClock" class="w-4 h-4 text-brand-primary shrink-0" />
              Válido até: <strong>{{ formatData(config.certificado_validade) }}</strong>
            </span>
          </div>
        </div>

        <BaseButton variant="primary" class="w-full sm:w-auto self-start" @click="openCertificadoModal">
          {{ config?.certificado_configurado ? 'Atualizar Certificado' : 'Configurar Certificado' }}
        </BaseButton>
      </div>

      <!-- 2. Emissão Estadual (NF-e, NFC-e) -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
                <LucideIcon :icon="Building" />
              </div>
              <div>
                <h3 class="text-base font-bold text-zinc-900">Emissão Estadual (NF-e / NFC-e)</h3>
                <p class="text-xs text-zinc-500">Parâmetros de numeração, séries e CSC</p>
              </div>
            </div>
            <!-- O ambiente exibido e o da PLATAFORMA quando ela responde. -->
            <span
              :class="[
                'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border',
                ambienteDivergente
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : ambienteVigente === 1
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-blue-50 text-blue-700 border-blue-200'
              ]"
              :title="ambienteDivergente
                ? 'A plataforma está em outro ambiente. Veja o cartão Plataforma de Emissão.'
                : undefined"
            >
              <LucideIcon v-if="ambienteDivergente" :icon="AlertCircle" class="w-3 h-3" />
              {{ ambienteVigente === 1 ? 'Produção' : 'Homologação' }}
            </span>
          </div>

          <!-- Resumo de parâmetros -->
          <div class="grid grid-cols-2 gap-3 mb-6">
            <div class="p-3 bg-zinc-50 rounded-xl border border-zinc-100">
              <span class="text-[11px] font-medium text-zinc-400 block">Série / Número NF-e</span>
              <span class="text-sm font-bold text-zinc-800">
                Série {{ config?.serie_nfe ?? 1 }} · Nº {{ config?.ultimo_numero_nfe ?? 0 }}
              </span>
            </div>
            <div class="p-3 bg-zinc-50 rounded-xl border border-zinc-100">
              <span class="text-[11px] font-medium text-zinc-400 block">Série / Número NFC-e</span>
              <span class="text-sm font-bold text-zinc-800">
                Série {{ config?.serie_nfce ?? 1 }} · Nº {{ config?.ultimo_numero_nfce ?? 0 }}
              </span>
            </div>
            <div class="col-span-2 p-3 bg-zinc-50 rounded-xl border border-zinc-100 flex items-center justify-between">
              <div>
                <span class="text-[11px] font-medium text-zinc-400 block">Token CSC (NFC-e)</span>
                <span class="text-xs font-semibold text-zinc-700">
                  {{ config?.csc_token ? `ID: ${config.csc_id || '000001'} · Configurado` : 'Não informado (Necessário p/ NFC-e)' }}
                </span>
              </div>
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  config?.csc_token ? 'bg-emerald-500' : 'bg-amber-400'
                ]"
              />
            </div>
          </div>
        </div>

        <BaseButton variant="primary" class="w-full sm:w-auto self-start" @click="openEstadualModal">
          Configurar Emissão Estadual
        </BaseButton>
      </div>

      <!-- 3. Tributação padrão da loja -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
                <LucideIcon :icon="Scale" />
              </div>
              <div>
                <h3 class="text-base font-bold text-zinc-900">Tributação Padrão</h3>
                <p class="text-xs text-zinc-500">A resposta que vale para o catálogo inteiro</p>
              </div>
            </div>
            <span
              :class="[
                'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border',
                tributacaoConfigurada
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200',
              ]"
            >
              {{ tributacaoConfigurada ? 'Configurada' : 'Não configurada' }}
            </span>
          </div>
          <p class="text-sm text-zinc-500 mb-6 leading-relaxed">
            Responda uma vez CFOP, origem e situação tributária, e cadastrar produto volta a ser
            nome, preço e NCM. O produto que foge da regra continua podendo ter tributação própria.
          </p>
        </div>
        <BaseButton variant="primary" class="w-full sm:w-auto self-start" @click="showTributacaoModal = true">
          {{ tributacaoConfigurada ? 'Revisar Tributação Padrão' : 'Configurar Tributação Padrão' }}
        </BaseButton>
      </div>

      <!-- 4. Emissão Municipal -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary">
              <LucideIcon :icon="MapPin" />
            </div>
            <div>
              <h3 class="text-base font-bold text-zinc-900">Emissão Municipal (NFS-e)</h3>
              <p class="text-xs text-zinc-500">Notas de Serviços e RPS junto à Prefeitura</p>
            </div>
          </div>
          <p class="text-sm text-zinc-500 mb-6 leading-relaxed">
            Integre com o portal tributário do seu município para emissão de notas fiscais de serviço a partir de Ordens de Serviço (OS).
          </p>
        </div>
        <BaseButton variant="secondary" class="w-full sm:w-auto self-start" disabled>
          Em breve
        </BaseButton>
      </div>
    </div>

    <!-- O outro lado do cano: sem isto, uma recusa da plataforma chega
         disfarcada de SEFAZ e nao ha como saber de quem e o problema. -->
    <FiscalPlataformaCard :configuracao="config" />

    <!-- Modais -->
    <FiscalCertificadoModal
      v-model:is-open="showCertificadoModal"
      @uploaded="aoEnviarCertificado"
    />
    <FiscalEmissaoEstadualModal
      v-model:is-open="showEstadualModal"
      :configuracao="config"
    />
    <FiscalTributacaoModal v-model:is-open="showTributacaoModal" />
  </div>
</template>
