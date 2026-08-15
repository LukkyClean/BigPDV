<script setup lang="ts">
/**
 * @view ConnectionErrorView
 * @description Tela de bloqueio exibida quando o terminal nao consegue
 *   conectar ao servidor remoto. Segue o padrao visual de LicenseErrorView.
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import BaseFooter from '@/shared/components/layout/BaseFooter.vue'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import { verificarSaude } from '@/shared/services/system/health.service' 
import AppLogo from '@/shared/components/AppLogo.vue'

const router = useRouter()
const networkStore = useNetworkConfigStore()
const { configAtual } = storeToRefs(networkStore)

const isRetrying = ref(false)
const retryError = ref('')

async function tentarNovamente() {
  isRetrying.value = true
  retryError.value = ''

  try {
    const ok = await verificarSaude(5000)
    if (ok) {
      networkStore.setErroConexaoTerminal(false)
      router.replace({ name: 'auth.user' })
    } else {
      retryError.value = 'O servidor continua indisponivel. Verifique se ele esta ligado e acessivel na rede.'
    }
  } catch {
    retryError.value = 'Falha ao tentar reconectar. Verifique sua rede e tente novamente.'
  } finally {
    isRetrying.value = false
  }
}

async function reconfigurarConexao() {
  router.push({ name: 'network-config' })
}
</script>

<template>
  <div class="h-screen flex flex-col items-center justify-between bg-white px-6 py-8">
    <div class="flex flex-col items-center flex-1 justify-center max-w-md w-full">
      <!-- Logo -->
      <div class="flex justify-center mb-6">
        <AppLogo class="h-16 w-auto" />
      </div>

      <!-- Icone e Titulo -->
      <div class="text-center mb-6">
        <span class="text-5xl mb-4 block">
          <svg class="w-14 h-14 mx-auto text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </span>
        <h1 class="text-2xl font-bold text-gray-800 mb-2">Servidor Indisponivel</h1>
      </div>

      <!-- Mensagem de Erro -->
      <div
        class="w-full bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center mb-6"
      >
        <template v-if="configAtual">
          Nao foi possivel conectar ao servidor em
          <strong>{{ configAtual.ip }}:{{ configAtual.port }}</strong>.
          Verifique se o servidor esta ligado e acessivel na rede.
        </template>
        <template v-else>
          Nao foi possivel estabelecer conexao com o servidor. Verifique suas configuracoes de rede.
        </template>
      </div>

      <!-- Erro do retry -->
      <div
        v-if="retryError"
        class="w-full bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm text-center mb-4"
      >
        {{ retryError }}
      </div>

      <!-- Botoes -->
      <div class="w-full space-y-3">
        <BaseButton
          type="button"
          class="w-full"
          :disabled="isRetrying"
          @click="tentarNovamente"
        >
          {{ isRetrying ? 'Verificando...' : 'Tentar Novamente' }}
        </BaseButton>

        <BaseButton
          type="button"
          variant="secondary"
          class="w-full"
          :disabled="isRetrying"
          @click="reconfigurarConexao"
        >
          Reconfigurar Conexao
        </BaseButton>
      </div>

      <!-- Orientacao -->
      <p class="text-xs text-gray-400 text-center mt-4">
        Para alterar o tipo de maquina, entre em contato com o suporte tecnico.
      </p>
    </div>

    <BaseFooter />
  </div>
</template>
