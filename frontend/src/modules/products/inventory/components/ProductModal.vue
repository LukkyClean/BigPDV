<script setup lang="ts">
/**
 * @component ProductModal
 * @description Modal for creating/editing products with multi-section form and image upload
 */

import { ref, watch, onMounted, onUnmounted } from 'vue';
import { X } from 'lucide-vue-next';

import { useProductModal } from '../composables/useProductModal';
import { useProductFormProvider } from '../composables/useProductForm';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import DadosProdutoSection from './form/DadosProdutoSection.vue';
import DadosEstoqueSection from './form/DadosEstoqueSection.vue';

// =============================================
// Modal State
// =============================================

const {
  isOpen,
  isCreateMode,
  isViewMode,
  modalTitle,
  closeModal,
} = useProductModal();

const { onSubmit, isPending, submitCount, apiError } = useProductFormProvider();

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
 * Handle backdrop click to close modal
 */
const gestoComecouNoFundo = ref(false);

function handleBackdropMousedown(event: MouseEvent) {
  gestoComecouNoFundo.value = (event.target as HTMLElement).classList.contains('modal-backdrop');
}

/**
 * Fecha ao clicar no fundo — mas só quando o clique COMEÇOU no fundo.
 *
 * Decidir pelo `click` fechava o modal no meio da edição: ao arrastar o mouse
 * para selecionar o texto de um campo e soltar fora dele, o navegador dispara o
 * `click` no ancestral comum entre onde apertou e onde soltou — o próprio
 * backdrop. Só acontecia com o mouse; com teclado nunca.
 */
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
            class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col mx-4"
          >
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
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

              <form id="product-form" @submit.prevent="onSubmit" class="space-y-8">
                <DadosProdutoSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                />

                <!-- Divider -->
                <div class="relative">
                  <div class="absolute inset-0 flex items-center">
                    <div class="w-full border-t border-zinc-200"></div>
                  </div>
                  <div class="relative flex justify-center">
                    <span
                      class="px-4 bg-white text-xs font-medium text-zinc-500 uppercase tracking-wider"
                    >
                      Dados de Estoque
                    </span>
                  </div>
                </div>

                <!-- Stock & Pricing Data -->
                <DadosEstoqueSection
                  :submit-count="submitCount"
                  :disabled="isViewMode"
                  :is-create-mode="isCreateMode"
                />
              </form>
            </div>

            <!-- Footer -->
            <div
              class="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-200 bg-zinc-50"
            >
              <BaseButton type="button" variant="secondary" @click="closeModal">
                {{ isViewMode ? 'Fechar' : 'Cancelar' }}
              </BaseButton>
              <BaseButton
                v-if="!isViewMode"
                type="submit"
                variant="primary"
                :is-loading="isPending"
                @click="onSubmit"
              >
                {{ isCreateMode ? 'Cadastrar Produto' : 'Salvar Alterações' }}
              </BaseButton>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
