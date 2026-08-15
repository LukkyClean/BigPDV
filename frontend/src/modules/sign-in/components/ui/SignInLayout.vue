<script setup lang="ts">
/**
 * @component SignInLayout
 * @description Layout principal do fluxo de sign-in com background decorativo
 * full-screen e card centralizado flutuante.
 */
import { ref, watch, nextTick } from 'vue';

import backgroundImage from '@/shared/assets/images/login/background.png';
import AppLogo from '@/shared/components/AppLogo.vue';

import BaseFooter from '@/shared/components/layout/BaseFooter.vue';

import { useSignIn } from '../../composables/useSignIn';

const { currentStep } = useSignIn();

const scrollContainer = ref<HTMLElement | null>(null);

watch(currentStep, async () => {
  await nextTick();

  if (scrollContainer.value) {
    scrollContainer.value.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  }
});
</script>

<template>
  <div class="h-screen relative overflow-hidden">
    <!-- Background full-screen -->
    <img
      :src="backgroundImage"
      alt="Background decorativo"
      class="absolute inset-0 w-full h-full object-cover"
    />

    <!-- Overlay sutil -->
    <div class="absolute inset-0 bg-black/5"></div>

    <!-- Container centralizado -->
    <div class="relative z-10 h-screen flex items-center justify-center p-4 lg:p-8 overflow-hidden">
      <!-- Card principal -->
      <div class="w-full max-w-3xl bg-white rounded-3xl shadow-2xl overflow-hidden">
        <!-- Header para Step 0 (Welcome) - Apenas logo centralizado -->
        <header v-if="currentStep === 0" class="px-8 lg:px-12 pt-8 pb-4">
          <div class="flex justify-center">
            <AppLogo class="h-16 w-auto" />
          </div>
        </header>

        <!-- Header para Steps 1-3 - Com título, progresso e logo -->
        <header v-else class="px-8 lg:px-12 pt-8 pb-4">
          <div class="flex items-start justify-between">
            <!-- Título e subtítulo -->
            <div class="flex-1">
              <h1 class="text-2xl lg:text-3xl font-bold text-brand-action mb-1">
                Configuração Inicial
              </h1>
              <p class="text-gray-500 text-sm">
                Configure sua empresa para começar a usar o sistema
              </p>

              <!-- Barra de progresso (4 segmentos) -->
              <div class="flex gap-2 mt-4">
                <div
                  v-for="i in 5"
                  :key="i"
                  class="flex-1 h-1.5 rounded-full transition-all duration-500"
                  :class="i <= currentStep ? 'bg-brand-primary' : 'bg-gray-200'"
                ></div>
              </div>
            </div>

            <!-- Logo -->
            <AppLogo class="h-16 w-auto ml-4" />
          </div>

          <!-- Indicador de etapa -->
          <p class="text-brand-primary font-medium text-sm mt-4">
            Etapa {{ currentStep }} de 5 -
            <span v-if="currentStep === 1">Tipo de Negócio</span>
            <span v-else-if="currentStep === 2">Dados da Loja</span>
            <span v-else-if="currentStep === 3">Dados do Responsável</span>
            <span v-else-if="currentStep === 4">Dados de Acesso</span>
            <span v-else-if="currentStep === 5">Confirmação</span>
          </p>
        </header>

        <!-- Conteúdo principal -->
        <main ref="scrollContainer" class="px-8 lg:px-12 py-6 max-h-[60vh] overflow-y-auto">
          <slot />
        </main>

        <!-- Footer dentro do card -->
        <footer class="px-8 lg:px-12 py-4 border-t border-gray-100 bg-gray-50/50">
          <BaseFooter />
        </footer>
      </div>
    </div>
  </div>
</template>
