<script setup lang="ts">
/**
 * @component EmpresaForm
 * @description Formulário principal de dados da empresa
 * Usa provide/inject pattern com VeeValidate
 * Todas as sections injetam context diretamente
 */

import { computed } from 'vue';
import { Building, Save } from 'lucide-vue-next';
import { onBeforeRouteLeave } from 'vue-router';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import { useConfirmacao } from '@/shared/composables/useConfirmacao';

// Section Components
import IdentificationSection from './form/IdentificationSection.vue';
import AddressSection from './form/AddressSection.vue';
import TaxDataSection from './form/TaxDataSection.vue';
import ContactSection from './form/ContactSection.vue';
import EmissaoStatusSection from './form/EmissaoStatusSection.vue';
// Emissão/Certificado (fiscal) saíram desta tela: a v1 é não-fiscal. A parte
// fiscal vive na tela separada /fiscal (gated por plano). Os componentes fiscais
// seguem preservados em ./form/, prontos para o módulo fiscal do próximo release.

import { useEmpresaFormProvider } from '../composables/useEmpresaFormProvider';

// =============================================
// Provider Setup
// =============================================

const {
  is_cnpj,
  documento,
  razao_social,
  apiError,
  isLoading,
  isPending,
  temAlteracoesPendentes,
  onSubmit,
} = useEmpresaFormProvider();

// O selo do cabeçalho olhava para `is_cnpj`, o que marcava toda empresa de CPF
// como "Cadastro Incompleto" para sempre. O que define completo é ter nome e
// documento — o tipo de pessoa é só uma característica do cadastro.
const cadastroCompleto = computed(
  () =>
    !!razao_social.value?.trim() &&
    documento.value.replace(/\D/g, '').length >= 11,
);

const seloCadastro = computed(() => {
  if (!cadastroCompleto.value) return 'Cadastro Incompleto';
  return is_cnpj.value ? 'Pessoa Jurídica' : 'Pessoa Física';
});

// =============================================
// Confirmações
// =============================================

const confirmacao = useConfirmacao();

async function handleSave(e?: Event) {
  e?.preventDefault();
  if (!temAlteracoesPendentes.value) return;

  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Salvar alterações da empresa?',
    descricao: 'As informações serão atualizadas imediatamente em todos os documentos futuros.',
    confirmLabel: 'Salvar',
    variant: 'warning',
  });

  if (ok) onSubmit();
}

// Avisa ao tentar sair com alterações não salvas.
// temAlteracoesPendentes usa comparação JSON (não meta.dirty do VeeValidate)
// para evitar falsos positivos no carregamento inicial da página.
onBeforeRouteLeave(async () => {
  if (!temAlteracoesPendentes.value) return true;

  return confirmacao.pedirConfirmacao({
    titulo: 'Sair sem salvar?',
    descricao: 'Você tem <strong>alterações não salvas</strong>. Se sair agora, todas as alterações serão perdidas.',
    confirmLabel: 'Sair sem salvar',
    cancelLabel: 'Continuar editando',
    variant: 'danger',
  });
});
</script>

<template>
  <div class="space-y-6">
    <!-- Error Banner -->
    <div
      v-if="apiError"
      class="p-4 bg-red-50 border border-red-200 rounded-lg"
    >
      <p class="text-sm text-red-600">{{ apiError }}</p>
    </div>

    <!-- Loading State -->
    <div
      v-if="isLoading"
      class="flex flex-col items-center justify-center py-20 bg-white rounded-xl shadow-sm border border-gray-100"
    >
      <span class="loading loading-spinner loading-lg text-brand-primary mb-4"></span>
      <p class="text-gray-500 font-medium animate-pulse">Carregando informações...</p>
    </div>

    <form v-else class="space-y-8 animate-in fade-in duration-500" @submit.prevent="handleSave">
      <!-- Header Card -->
      <div
        class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-start justify-between"
      >
        <div>
          <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
            <Building class="text-brand-primary" :size="24" />
            Dados da Organização
          </h2>
          <p class="text-sm text-gray-500 mt-1">
            Mantenha os dados da sua empresa sempre atualizados para emissão de documentos.
          </p>
        </div>
        <div class="hidden md:block">
          <span
            class="px-3 py-1 bg-brand-primary-light text-brand-primary text-xs font-bold uppercase rounded-full tracking-wide"
          >
            {{ seloCadastro }}
          </span>
          <!--
            O selo de ambiente (Homologação/Produção) saiu daqui: é conceito de
            emissão de NF-e e pertence ao módulo Fiscal, que na v1 é um estado
            BLOQUEADO com CTA de upgrade e não expõe configuração fiscal
            (ver FiscalView.vue). Nesta tela ele anunciava um ambiente de emissão
            para um recurso que o plano nem libera.
          -->

        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Left Column: Forms -->
        <div class="lg:col-span-2 space-y-8">
          <!-- Todas as sections injetam context via useEmpresaForm() -->
          <IdentificationSection />
          <AddressSection />
          <!-- Dados Fiscais são exclusivos de PJ: IE, regime tributário,
               natureza jurídica e CNAE não existem para uma pessoa física. -->
          <TaxDataSection v-if="is_cnpj" />
          <ContactSection />

          <!-- Acesso à tela fiscal (separada). Sem o módulo NF-e continua
               sendo o upsell bloqueado; com o módulo, passa a dizer se o
               cadastro desta empresa já permite emitir. -->
          <EmissaoStatusSection />
        </div>

        <!-- Right Column: Actions -->
        <div class="space-y-6">
          <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 sticky top-6">
            <h3 class="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Ações</h3>
            <p class="text-sm text-gray-500 mb-6 leading-relaxed">
              Ao salvar, as informações serão atualizadas em todos os orçamentos e ordens de
              serviço futuros.
            </p>
            <BaseButton
              type="submit"
              variant="primary"
              :is-loading="isPending"
              :disabled="!temAlteracoesPendentes"
              class="w-full justify-center py-3 text-sm font-bold shadow-brand-primary-light/20 shadow-lg hover:shadow-brand-primary-light/30 transition-all transform active:scale-95"
            >
              <Save :size="18" class="mr-2" />
              Salvar Alterações
            </BaseButton>
            <div class="mt-4 pt-4 border-t border-gray-100 text-center">
              <span class="text-xs text-gray-400">Última atualização: Hoje</span>
            </div>
          </div>
        </div>
      </div>
    </form>
  </div>

  <!-- Modal de confirmação (salvar + sair sem salvar) -->
  <BaseConfirmModal
    :is-open="confirmacao.isOpen.value"
    :title="confirmacao.opcoes.value.titulo"
    :description="confirmacao.opcoes.value.descricao"
    :confirm-label="confirmacao.opcoes.value.confirmLabel"
    :cancel-label="confirmacao.opcoes.value.cancelLabel"
    :variant="confirmacao.opcoes.value.variant"
    :is-loading="isPending"
    @confirm="confirmacao.confirmar"
    @close="confirmacao.cancelar"
  />
</template>
