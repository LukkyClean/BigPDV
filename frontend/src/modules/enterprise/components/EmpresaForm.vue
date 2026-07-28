<script setup lang="ts">
/**
 * @component EmpresaForm
 * @description Formulário principal de dados da empresa
 * Usa provide/inject pattern com VeeValidate
 * Todas as sections injetam context diretamente
 */

import { Building, Save, Globe, FileText, Lock, ChevronRight } from 'lucide-vue-next';
import { onBeforeRouteLeave, useRouter } from 'vue-router';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import { useConfirmacao } from '@/shared/composables/useConfirmacao';

// Section Components
import IdentificationSection from './form/IdentificationSection.vue';
import AddressSection from './form/AddressSection.vue';
import TaxDataSection from './form/TaxDataSection.vue';
import ContactSection from './form/ContactSection.vue';
// Emissão/Certificado (fiscal) saíram desta tela: a v1 é não-fiscal. A parte
// fiscal vive na tela separada /fiscal (gated por plano). Os componentes fiscais
// seguem preservados em ./form/, prontos para o módulo fiscal do próximo release.

import { useEmpresaFormProvider } from '../composables/useEmpresaFormProvider';
import { recursoDisponivel } from '@/shared/config/planos';

// =============================================
// Provider Setup
// =============================================

const {
  is_cnpj,
  fiscal_settings,
  apiError,
  isLoading,
  isPending,
  temAlteracoesPendentes,
  onSubmit,
} = useEmpresaFormProvider();

// =============================================
// Confirmações
// =============================================

const confirmacao = useConfirmacao();
const router = useRouter();
const nfeDisponivel = recursoDisponivel('nfe');

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
            {{ is_cnpj ? 'Empresa Verificada' : 'Cadastro Incompleto' }}
          </span>
          <span
            v-if="fiscal_settings"
            class="ml-2 px-3 py-1 text-xs font-bold uppercase rounded-full tracking-wide border"
            :class="
              fiscal_settings.ambiente_emissao === 1
                ? 'bg-red-50 text-red-600 border-red-200'
                : 'bg-brand-primary-light text-brand-primary border-brand-primary/20'
            "
          >
            <Globe :size="12" class="inline mb-0.5 mr-1" />
            {{ fiscal_settings.ambiente_emissao === 1 ? 'Produção' : 'Homologação' }}
          </span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Left Column: Forms -->
        <div class="lg:col-span-2 space-y-8">
          <!-- Todas as sections injetam context via useEmpresaForm() -->
          <IdentificationSection />
          <AddressSection />
          <TaxDataSection />
          <ContactSection />

          <!-- Acesso à tela fiscal (separada). Na v1 (plano Start) é um upsell
               bloqueado; toca em /fiscal onde fica o CTA de upgrade. -->
          <button
            type="button"
            class="w-full flex items-center gap-4 bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:border-brand-primary/40 hover:shadow transition-all text-left"
            @click="router.push('/fiscal')"
          >
            <div class="w-11 h-11 rounded-xl bg-brand-primary-light flex items-center justify-center shrink-0">
              <FileText :size="20" class="text-brand-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-bold text-gray-800">Emissão de Notas Fiscais</h3>
                <span
                  v-if="!nfeDisponivel"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px] font-bold uppercase"
                >
                  <Lock :size="10" /> Plano superior
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">
                {{ nfeDisponivel
                  ? 'Configure a emissão de NF-e, NFC-e e NFS-e.'
                  : 'Não incluído no seu plano. Toque para fazer upgrade.' }}
              </p>
            </div>
            <ChevronRight :size="18" class="text-gray-400 shrink-0" />
          </button>
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
              :loading="isPending"
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
