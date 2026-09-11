<script setup lang="ts">
/**
 * @view ConnectionErrorView
 * @description Tela de bloqueio exibida quando não há backend alcançável.
 *   - Terminal: o servidor remoto não respondeu. Tenta reconectar sozinha a cada
 *     10 s (ping + redescoberta mDNS — cobre servidor que trocou de IP ou que
 *     ainda está subindo) e oferece configuração manual.
 *   - Servidor: o serviço local (erp-api) não respondeu. Oferece reiniciar/reparar
 *     o serviço. NUNCA leva ao wizard de "Tipo de máquina": esta máquina já é o
 *     servidor, e reescolher o papel foi o que a transformava em terminal.
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import BaseFooter from '@/shared/components/layout/BaseFooter.vue'
import AppLogo from '@/shared/components/AppLogo.vue'
import DiagnosticoConexao from '@/shared/components/DiagnosticoConexao.vue'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import { tentarReconectar } from '@/shared/services/system/reconexao.service'

const INTERVALO_RETRY_S = 10

const router = useRouter()
const networkStore = useNetworkConfigStore()
const { configAtual, papel } = storeToRefs(networkStore)

const isServidor = computed(() => papel.value === 'servidor')

const isRetrying = ref(false)
const ultimaTentativa = ref<Date | null>(null)
const tentativas = ref(0)
const segundosParaProxima = ref(INTERVALO_RETRY_S)
const mostrarDiagnostico = ref(false)
const diagnosticoRef = ref<InstanceType<typeof DiagnosticoConexao> | null>(null)

let timer: ReturnType<typeof setInterval> | null = null

const titulo = computed(() =>
  isServidor.value ? 'Serviço local não respondeu' : 'Servidor indisponível',
)

const mensagem = computed(() => {
  if (isServidor.value) {
    return `O serviço do StartBig nesta máquina (erp-api) não respondeu na porta ${configAtual.value?.port ?? ''}. `
      + 'Ele costuma levar até 2 minutos para iniciar após ligar o computador.'
  }
  if (configAtual.value) {
    return `Não foi possível conectar ao servidor em ${configAtual.value.ip}:${configAtual.value.port}. `
      + 'Verifique se o computador servidor está ligado e conectado à rede local.'
  }
  return 'Não foi possível conectar ao servidor. Verifique se o computador servidor está ligado e conectado à rede local.'
})

async function tentarAgora() {
  if (isRetrying.value) return
  isRetrying.value = true
  tentativas.value++

  try {
    const resultado = await tentarReconectar({ timeoutDiscoveryMs: 6000 })
    ultimaTentativa.value = new Date()

    if (resultado.ok) {
      networkStore.setSemConexaoBackend(false)
      router.replace({ name: 'auth.user' })
      return
    }
  } finally {
    isRetrying.value = false
    segundosParaProxima.value = INTERVALO_RETRY_S
    diagnosticoRef.value?.carregar()
  }
}

function reconfigurarConexao() {
  router.push({ name: 'network-config' })
}

onMounted(() => {
  timer = setInterval(() => {
    if (isRetrying.value) return
    segundosParaProxima.value--
    if (segundosParaProxima.value <= 0) {
      void tentarAgora()
    }
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-between bg-white px-6 py-8">
    <div class="flex flex-col items-center flex-1 justify-center max-w-md w-full">
      <!-- Logo -->
      <div class="flex justify-center mb-6">
        <AppLogo class="h-16 w-auto" />
      </div>

      <!-- Ícone e título -->
      <div class="text-center mb-6">
        <span class="text-5xl mb-4 block">
          <svg class="w-14 h-14 mx-auto text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </span>
        <h1 class="text-2xl font-bold text-gray-800 mb-2">{{ titulo }}</h1>
      </div>

      <!-- Mensagem -->
      <div class="w-full bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center mb-4">
        {{ mensagem }}
      </div>

      <!-- Estado do retry automático -->
      <div class="w-full bg-gray-50 border border-gray-200 text-gray-600 px-4 py-2.5 rounded-lg text-xs text-center mb-6 flex items-center justify-center gap-2">
        <span
          v-if="isRetrying"
          class="inline-block w-3.5 h-3.5 border-2 border-gray-300 border-t-brand-primary rounded-full animate-spin"
        ></span>
        <span v-if="isRetrying">
          {{ isServidor ? 'Verificando o serviço local…' : 'Procurando o servidor na rede local…' }}
        </span>
        <span v-else>
          Nova tentativa automática em {{ segundosParaProxima }} s
          <template v-if="ultimaTentativa">
            · última às {{ ultimaTentativa.toLocaleTimeString('pt-BR') }}
          </template>
        </span>
      </div>

      <!-- Botões -->
      <div class="w-full space-y-3">
        <BaseButton type="button" class="w-full" :disabled="isRetrying" @click="tentarAgora">
          {{ isRetrying ? 'Verificando...' : 'Tentar agora' }}
        </BaseButton>

        <BaseButton
          v-if="!isServidor"
          type="button"
          variant="secondary"
          class="w-full"
          :disabled="isRetrying"
          @click="reconfigurarConexao"
        >
          Configurar endereço manualmente
        </BaseButton>

        <button
          type="button"
          class="w-full text-xs text-brand-primary hover:underline cursor-pointer py-1"
          @click="mostrarDiagnostico = !mostrarDiagnostico"
        >
          {{ mostrarDiagnostico ? 'Ocultar diagnóstico' : (isServidor ? 'Reiniciar serviço / diagnóstico' : 'Ver diagnóstico') }}
        </button>
      </div>

      <div v-if="mostrarDiagnostico" class="w-full mt-4 border border-gray-200 rounded-xl p-4">
        <DiagnosticoConexao ref="diagnosticoRef" />
      </div>

      <!-- Orientação -->
      <p class="text-xs text-gray-400 text-center mt-4">
        Para alterar o tipo de máquina (servidor/terminal), entre em contato com o suporte técnico.
      </p>
    </div>

    <BaseFooter />
  </div>
</template>
