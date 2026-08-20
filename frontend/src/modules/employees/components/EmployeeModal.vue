<script setup lang="ts">
/**
 * @component EmployeeModal
 * @description Modal for creating/editing employees with multi-section form
 */

import { ref, watch, onMounted, onUnmounted } from 'vue';
import { X } from 'lucide-vue-next';

import { useEmployeeModal } from '../composables/useEmployeeModal';
import { useEmployeeFormProvider } from '../composables/useEmployeeForm';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import DadosFuncionarioSection from './form/DadosFuncionarioSection.vue';
import EnderecoSection from './form/EnderecoSection.vue';
import DadosBancariosSection from './form/DadosBancariosSection.vue';
import ComissaoSection from './form/ComissaoSection.vue';
import ObservacoesSection from './form/ObservacoesSection.vue';

// =============================================
// Modal State
// =============================================

const {
  isOpen,
  isCreateMode,
  isViewMode,
  modalTitle,
  closeModal,
} = useEmployeeModal();

// Initialize form provider - this provides form context to all child components
const {
  onSubmit,
  isPending,
  submitCount,
  apiError,
  funcionarioSemAcesso,
} = useEmployeeFormProvider();

// =============================================
// Event Handlers
// =============================================

/**
 * Handle ESC key to close modal
 */
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    closeModal();
  }
}

/**
 * Fecha ao clicar no fundo — mas só quando o clique COMEÇOU no fundo.
 *
 * Decidir pelo `click` fechava o modal no meio da edição: ao arrastar o mouse
 * para selecionar o texto de um campo e soltar fora dele, o navegador dispara o
 * `click` no ancestral comum entre onde apertou e onde soltou — o próprio
 * backdrop. O `event.target` era o backdrop, a checagem passava, e a edição ia
 * embora. Só acontecia com o mouse; com teclado (Ctrl+A) nunca.
 *
 * `mousedown` registra onde o gesto NASCEU; o clique só fecha se nasceu e
 * terminou no fundo.
 */
const gestoComecouNoFundo = ref(false);

function handleBackdropMousedown(event: MouseEvent) {
  gestoComecouNoFundo.value = (event.target as HTMLElement).classList.contains('modal-backdrop');
}

function handleBackdropClick(event: MouseEvent) {
  const terminouNoFundo = (event.target as HTMLElement).classList.contains('modal-backdrop');
  if (gestoComecouNoFundo.value && terminouNoFundo) {
    closeModal();
  }
  gestoComecouNoFundo.value = false;
}

// =============================================
// Lifecycle
// =============================================

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});

// Prevent body scroll when modal is open
watch(isOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : '';
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="modal-backdrop fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        @mousedown="handleBackdropMousedown"
        @click="handleBackdropClick"
      >
        <Transition
          enter-active-class="transition ease-out duration-300"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition ease-in duration-200"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 translate-y-4"
        >
          <div
            v-if="isOpen"
            class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col mx-4"
            @click.stop
          >
            <!-- Header -->
            <div
              class="flex items-center justify-between px-6 py-4 border-b border-zinc-200"
            >
              <h2 class="text-xl font-bold text-zinc-800">
                {{ modalTitle }}
              </h2>
              <button
                type="button"
                class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                @click="closeModal"
              >
                <X :size="20" />
              </button>
            </div>

            <!-- Body (scrollable) -->
            <div class="flex-1 overflow-y-auto px-6 py-6">
              <!-- API Error Alert -->
              <div
                v-if="apiError"
                class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm"
              >
                {{ apiError }}
              </div>

              <form id="employee-form" @submit.prevent="onSubmit" class="space-y-8">
                <!-- Dados do Funcionario -->
                <DadosFuncionarioSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                  :show-user-fields="isCreateMode || funcionarioSemAcesso"
                />

                <!-- Endereco -->
                <EnderecoSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                />

                <!-- Dados Bancarios -->
                <DadosBancariosSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                />

                <!-- Comissão (override do cargo) -->
                <ComissaoSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                />

                <!-- Observacoes -->
                <ObservacoesSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                />
              </form>
            </div>

            <!-- Footer -->
            <div
              class="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-200 bg-zinc-50"
            >
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
                {{ isCreateMode ? 'Cadastrar' : 'Salvar Alteracoes' }}
              </BaseButton>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
