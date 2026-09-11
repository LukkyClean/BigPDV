<script setup lang="ts">
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { useNetworkConfig } from '../composables/useNetworkConfig'

const { tipoMaquina, portaConfigurada, tentandoConexao, erroConexao, sugerirServidor, tentarNovamente, configurarComoServidor, voltar } = useNetworkConfig()
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div v-if="tentandoConexao" class="flex flex-col items-center gap-4 py-8">
      <div class="w-12 h-12 border-4 border-gray-200 border-t-brand-primary rounded-full animate-spin"></div>
      <div class="text-center space-y-1">
        <p class="text-base font-semibold text-gray-800">
          {{ tipoMaquina === 'servidor' ? 'Iniciando servidor...' : 'Conectando ao servidor...' }}
        </p>
        <p class="text-sm text-gray-500">
          {{ tipoMaquina === 'servidor' ? 'Aguarde enquanto o serviço local é inicializado (pode levar até 2 minutos)' : 'Verificando comunicação com o servidor' }}
        </p>
        <p v-if="tipoMaquina === 'servidor' && portaConfigurada" class="text-xs text-gray-400 mt-2">
          Porta: {{ portaConfigurada }}
        </p>
      </div>
    </div>

    <!-- Erro -->
    <div v-else-if="erroConexao" class="space-y-4">
      <div class="flex flex-col items-center gap-3 py-4">
        <div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
          <svg class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <div class="text-center space-y-1">
          <p class="text-base font-semibold text-gray-800">Falha na conexão</p>
          <p class="text-sm text-gray-500 max-w-sm">{{ erroConexao }}</p>
        </div>
      </div>

      <BaseButton v-if="sugerirServidor" class="w-full" @click="configurarComoServidor">
        Configurar esta máquina como Servidor
      </BaseButton>

      <div class="flex gap-3">
        <BaseButton variant="secondary" @click="voltar">
          Voltar
        </BaseButton>
        <BaseButton class="flex-1" :variant="sugerirServidor ? 'secondary' : 'primary'" @click="tentarNovamente">
          {{ sugerirServidor ? 'Informar outro endereço' : 'Tentar novamente' }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>
