<script setup lang="ts">
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useServicoModal } from '../composables/useServicoModal';
import { useServicoFormProvider } from '../composables/useServicoForm';
import { recursoDisponivel } from '@/shared/config/planos';
import ServicoDadosSection from './form/ServicoDadosSection.vue';
import DadosFiscaisSection from './form/DadosFiscaisSection.vue';

const { isOpen, isCreateMode, isViewMode, modalTitle, closeModal } = useServicoModal();
const { onSubmit, isPending, submitCount, apiError } = useServicoFormProvider();

const nfeDisponivel = recursoDisponivel('nfe');
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="modalTitle"
    size="lg"
    @close="closeModal"
  >
    <div>
      <div
        v-if="apiError"
        class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm"
      >
        {{ apiError }}
      </div>

      <form id="servico-form" @submit.prevent="onSubmit" class="space-y-8">
        <ServicoDadosSection :submit-count="submitCount" :disabled="isViewMode" />

        <!-- Dados Fiscais — visível apenas para licenças com módulo fiscal ativo -->
        <template v-if="nfeDisponivel">
          <!-- Divider -->
          <div class="relative">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-zinc-200"></div>
            </div>
            <div class="relative flex justify-center">
              <span class="px-4 bg-white text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Dados Fiscais
              </span>
            </div>
          </div>

          <DadosFiscaisSection
            :submit-count="submitCount"
            :disabled="isViewMode"
            :is-create-mode="isCreateMode"
          />
        </template>
      </form>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full">
        <BaseButton
          type="button"
          variant="secondary"
          @click="closeModal"
        >
          {{ isViewMode ? 'Fechar' : 'Cancelar' }}
        </BaseButton>
        <BaseButton
          v-if="!isViewMode"
          type="submit"
          variant="primary"
          :is-loading="isPending"
          @click="onSubmit"
        >
          {{ isCreateMode ? 'Cadastrar Serviço' : 'Salvar Alterações' }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
