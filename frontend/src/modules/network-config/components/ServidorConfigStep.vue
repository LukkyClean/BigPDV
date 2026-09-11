<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue'
import { useNetworkConfig } from '../composables/useNetworkConfig'

const { ipLocal, carregarIpLocal, configurarServidor, voltar } = useNetworkConfig()

const mostrarPortaCustom = ref(false)
const portaCustom = ref<string>('')
const carregando = ref(false)

onMounted(() => {
  carregarIpLocal()
})

async function iniciarServidor() {
  carregando.value = true
  const porta = mostrarPortaCustom.value && portaCustom.value
    ? Number(portaCustom.value)
    : undefined
  await configurarServidor(porta)
  carregando.value = false
}
</script>

<template>
  <div class="space-y-5">
    <div>
      <h2 class="text-lg font-bold text-gray-800">Configurar Servidor</h2>
      <p class="text-sm text-gray-500 mt-1">
        O sistema irá iniciar o servidor automaticamente nesta máquina.
      </p>
    </div>

    <!-- IP local da máquina -->
    <div class="p-4 bg-blue-50 border border-blue-100 rounded-xl space-y-1">
      <p class="text-xs font-medium text-blue-700">IP desta máquina na rede</p>
      <p class="text-lg font-bold text-blue-900 font-mono">{{ ipLocal || 'Detectando...' }}</p>
      <p class="text-xs text-blue-600">
        Informe este IP aos terminais que irão conectar a este servidor
      </p>
    </div>

    <!-- Recomendação operacional: sem IP fixo, o endereço muda ao ligar a máquina -->
    <div class="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-100 rounded-xl">
      <svg class="w-5 h-5 text-amber-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <p class="text-xs text-amber-700">
        Recomendado: configure um <strong>IP fixo</strong> (ou reserva DHCP) para este computador no
        roteador e desative a "Inicialização Rápida" do Windows. Sem isso o IP pode mudar ao ligar
        a máquina e os terminais perdem o servidor.
      </p>
    </div>

    <!-- Toggle porta customizada -->
    <div>
      <button
        type="button"
        class="text-sm text-brand-primary hover:underline cursor-pointer"
        @click="mostrarPortaCustom = !mostrarPortaCustom"
      >
        {{ mostrarPortaCustom ? 'Usar porta automática' : 'Definir porta manualmente' }}
      </button>

      <div v-if="mostrarPortaCustom" class="mt-3">
        <BaseInput
          v-model="portaCustom"
          type="number"
          label="Porta"
          placeholder="Ex: 8080"
        />
      </div>
    </div>

    <!-- Ações -->
    <div class="flex gap-3 pt-2">
      <BaseButton variant="secondary" @click="voltar">
        Voltar
      </BaseButton>
      <BaseButton class="flex-1" :is-loading="carregando" @click="iniciarServidor">
        Iniciar Servidor
      </BaseButton>
    </div>
  </div>
</template>
