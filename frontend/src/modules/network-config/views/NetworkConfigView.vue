<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useNetworkConfig } from '../composables/useNetworkConfig'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import TipoMaquinaStep from '../components/TipoMaquinaStep.vue'
import ServidorConfigStep from '../components/ServidorConfigStep.vue'
import TerminalConfigStep from '../components/TerminalConfigStep.vue'
import ConexaoStatusStep from '../components/ConexaoStatusStep.vue'

import backgroundImage from '@/shared/assets/images/login/background.png'
import AppLogo from '@/shared/components/AppLogo.vue'
import BaseFooter from '@/shared/components/layout/BaseFooter.vue'

const { currentStep, tipoMaquina, resetConfig, iniciarModoTerminalOnly } = useNetworkConfig()
const networkStore = useNetworkConfigStore()

onMounted(() => {
  if (networkStore.erroConexaoTerminal) {
    iniciarModoTerminalOnly()
  }
})

const currentStepComponent = computed(() => {
  if (currentStep.value === 0) return TipoMaquinaStep
  if (currentStep.value === 2) return ConexaoStatusStep
  // Step 1: depende do tipo
  return tipoMaquina.value === 'servidor' ? ServidorConfigStep : TerminalConfigStep
})

onUnmounted(() => {
  resetConfig()
})
</script>

<template>
  <div class="h-screen relative overflow-hidden">
    <img
      :src="backgroundImage"
      alt="Background decorativo"
      class="absolute inset-0 w-full h-full object-cover"
    />
    <div class="absolute inset-0 bg-black/5"></div>

    <div class="relative z-10 h-screen flex items-center justify-center p-4 lg:p-8 overflow-hidden">
      <div class="w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden">
        <!-- Header -->
        <header class="px-8 pt-8 pb-4">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-xl font-bold text-brand-action">Configuração de Rede</h1>
              <p class="text-gray-500 text-xs mt-0.5">Configure a comunicação do sistema</p>
            </div>
            <AppLogo class="h-12 w-auto" />
          </div>
        </header>

        <!-- Conteúdo -->
        <main class="px-8 py-6">
          <Transition
            mode="out-in"
            enter-active-class="transition-all duration-300 ease-out"
            enter-from-class="opacity-0 translate-x-4"
            enter-to-class="opacity-100 translate-x-0"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 translate-x-0"
            leave-to-class="opacity-0 -translate-x-4"
          >
            <component :is="currentStepComponent" :key="`${currentStep}-${tipoMaquina}`" />
          </Transition>
        </main>

        <!-- Footer -->
        <footer class="px-8 py-4 border-t border-gray-100 bg-gray-50/50">
          <BaseFooter />
        </footer>
      </div>
    </div>
  </div>
</template>
