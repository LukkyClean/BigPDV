<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQueryClient } from '@tanstack/vue-query';
import { Shield, Building, MapPin, CheckCircle, AlertCircle, FileCheck, ArrowLeft } from 'lucide-vue-next';
import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import FiscalCertificadoModal from '../components/configuracoes/FiscalCertificadoModal.vue';
import FiscalEmissaoEstadualModal from '../components/configuracoes/FiscalEmissaoEstadualModal.vue';
import { useFiscalConfiguracaoQuery } from '../composables/useFiscalConfiguracaoQuery';
import { fiscalKeys } from '../constants/fiscal.constants';

const showCertificadoModal = ref(false);
const showEstadualModal = ref(false);

const { data: config, isLoading } = useFiscalConfiguracaoQuery();
const queryClient = useQueryClient();
const router = useRouter();

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
            <span
              v-if="config?.certificado_configurado"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
            >
              <LucideIcon :icon="CheckCircle" class="w-3.5 h-3.5" />
              Conectado
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

          <div v-if="config?.certificado_cnpj" class="mb-6 p-3 rounded-xl bg-zinc-50 border border-zinc-100 text-xs text-zinc-600 flex items-center gap-2">
            <LucideIcon :icon="FileCheck" class="w-4 h-4 text-brand-primary shrink-0" />
            <span>CNPJ Vinculado: <strong>{{ config.certificado_cnpj }}</strong></span>
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
            <span
              :class="[
                'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border',
                config?.ambiente === 1
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-blue-50 text-blue-700 border-blue-200'
              ]"
            >
              {{ config?.ambiente === 1 ? 'Produção' : 'Homologação' }}
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

      <!-- 3. Emissão Municipal -->
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

    <!-- Modais -->
    <FiscalCertificadoModal
      v-model:is-open="showCertificadoModal"
      @uploaded="aoEnviarCertificado"
    />
    <FiscalEmissaoEstadualModal
      v-model:is-open="showEstadualModal"
      :configuracao="config"
    />
  </div>
</template>
