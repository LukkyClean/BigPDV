<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { useForm } from 'vee-validate';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { useNetworkConfig } from '../composables/useNetworkConfig';
import { useAutoDiscovery } from '../composables/useAutoDiscovery';
import { terminalConfigTypedSchema } from '../schemas/network-config.schema';

const { configurarTerminal, configurarComoServidor, voltar } = useNetworkConfig();
const { estado, servidorEncontrado, iniciarBusca, pararBusca, reiniciarBusca } = useAutoDiscovery();

const modoManual = ref(false);
const countdown = ref(3);

// VeeValidate para modo manual
const { defineField, handleSubmit, errors } = useForm({
  validationSchema: terminalConfigTypedSchema,
  initialValues: { serverIp: '', serverPort: 8080 },
});
const [serverIp, serverIpAttrs] = defineField('serverIp');
const [serverPort, serverPortAttrs] = defineField('serverPort');

const onSubmitManual = handleSubmit(async (values) => {
  await configurarTerminal(values.serverIp, values.serverPort);
});

// Inicia auto-descoberta ao montar
onMounted(() => {
  iniciarBusca();
});

// Countdown e auto-conexao quando servidor encontrado
let countdownInterval: ReturnType<typeof setInterval> | null = null;

watch(estado, (novo) => {
  if (novo === 'encontrado' && servidorEncontrado.value) {
    // O servidor encontrado roda NESTA máquina: não auto-conectar como terminal
    // (gravaria o próprio IP de LAN, que muda com o DHCP). Oferecer o papel certo.
    if (servidorEncontrado.value.local) return;
    countdown.value = 3;
    countdownInterval = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0 && servidorEncontrado.value) {
        limparCountdown();
        configurarTerminal(servidorEncontrado.value.ip, servidorEncontrado.value.port);
      }
    }, 1000);
  }
});

function limparCountdown() {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
}

function conectarAgora() {
  if (servidorEncontrado.value) {
    limparCountdown();
    configurarTerminal(servidorEncontrado.value.ip, servidorEncontrado.value.port);
  }
}

function irParaManual() {
  limparCountdown();
  pararBusca();
  modoManual.value = true;
}

function voltarParaBusca() {
  modoManual.value = false;
  reiniciarBusca();
}

onUnmounted(() => {
  limparCountdown();
});
</script>

<template>
  <div class="space-y-5">
    <!-- Estado: Buscando -->
    <template v-if="estado === 'buscando' && !modoManual">
      <div class="flex flex-col items-center gap-4 py-8">
        <div
          class="w-12 h-12 border-4 border-gray-200 border-t-brand-primary rounded-full animate-spin"
        ></div>
        <div class="text-center space-y-1">
          <p class="text-base font-semibold text-gray-800">Buscando servidor automaticamente...</p>
          <p class="text-sm text-gray-500">Procurando servidores StartBig na rede local</p>
        </div>
      </div>

      <div class="flex flex-col items-center gap-3">
        <BaseButton variant="secondary" @click="voltar"> Voltar </BaseButton>
        <button
          type="button"
          class="text-sm text-brand-primary hover:underline cursor-pointer"
          @click="irParaManual"
        >
          Pular e configurar manualmente
        </button>
      </div>
    </template>

    <!-- Estado: Encontrado nesta própria máquina -->
    <template v-else-if="estado === 'encontrado' && !modoManual && servidorEncontrado?.local">
      <div class="flex flex-col items-center gap-4 py-4">
        <div class="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
          <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2a4 4 0 014-4h5m0 0l-3-3m3 3l-3 3M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        <div class="text-center space-y-1">
          <p class="text-base font-semibold text-gray-800">O servidor está neste computador</p>
          <p class="text-sm text-gray-500">
            O serviço StartBig foi encontrado rodando nesta própria máquina
            (<span class="font-mono">{{ servidorEncontrado.ip }}:{{ servidorEncontrado.port }}</span>).
            Ela deve operar como <strong>Servidor</strong>, não como terminal.
          </p>
        </div>
      </div>

      <div class="flex flex-col gap-3 pt-2">
        <BaseButton class="w-full" @click="configurarComoServidor"> Configurar como Servidor </BaseButton>
        <div class="flex gap-3">
          <BaseButton class="flex-1" variant="secondary" @click="voltar"> Voltar </BaseButton>
          <BaseButton class="flex-1" variant="secondary" @click="irParaManual"> Informar outro servidor </BaseButton>
        </div>
      </div>
    </template>

    <!-- Estado: Encontrado -->
    <template v-else-if="estado === 'encontrado' && !modoManual && servidorEncontrado">
      <div class="flex flex-col items-center gap-4 py-4">
        <div class="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
          <svg
            class="w-6 h-6 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div class="text-center space-y-1">
          <p class="text-base font-semibold text-gray-800">Servidor encontrado!</p>
          <p class="text-lg font-bold text-brand-primary font-mono">
            {{ servidorEncontrado.ip }}:{{ servidorEncontrado.port }}
          </p>
        </div>
      </div>

      <!-- Barra de countdown -->
      <div class="space-y-2">
        <div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
          <div
            class="bg-brand-primary h-1.5 rounded-full transition-all duration-1000 ease-linear"
            :style="{ width: `${(countdown / 3) * 100}%` }"
          ></div>
        </div>
        <p class="text-xs text-gray-500 text-center">
          Conectando automaticamente em {{ countdown }}s...
        </p>
      </div>

      <div class="flex gap-3 pt-2">
        <BaseButton variant="secondary" @click="irParaManual"> Configurar manualmente </BaseButton>
        <BaseButton class="flex-1" @click="conectarAgora"> Conectar agora </BaseButton>
      </div>
    </template>

    <!-- Estado: Timeout (sem servidor encontrado) -->
    <template v-else-if="estado === 'timeout' && !modoManual">
      <div class="flex flex-col items-center gap-4 py-4">
        <div class="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
          <svg
            class="w-6 h-6 text-amber-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
        </div>
        <div class="text-center space-y-1">
          <p class="text-base font-semibold text-gray-800">Nenhum servidor encontrado</p>
          <p class="text-sm text-gray-500">
            Nao foi possivel detectar um servidor StartBig na rede local.
          </p>
        </div>
      </div>

      <div class="flex flex-col gap-4 pt-2">
        <div class="flex gap-3">
          <BaseButton class="flex-1" variant="secondary" @click="voltar"> Voltar </BaseButton>
          <BaseButton class="w-[70%]" variant="primary" @click="voltarParaBusca">
            Buscar novamente
          </BaseButton>
        </div>
        <a class="text-sm font-medium text-brand-primary cursor-pointer hover:underline" @click="modoManual = true">Configurar manualmente</a>
      </div>
    </template>

    <!-- Estado: Formulario Manual -->
    <template v-else>
      <div>
        <h2 class="text-lg font-bold text-gray-800">Conectar ao Servidor</h2>
        <p class="text-sm text-gray-500 mt-1">Informe o endereco do servidor na rede local.</p>
      </div>

      <!-- Tip card -->
      <div class="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-100 rounded-xl">
        <svg
          class="w-5 h-5 text-amber-500 mt-0.5 shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
        <p class="text-xs text-amber-700">
          Verifique o IP e a porta nas configuracoes do ERP no computador que esta atuando como
          servidor.
        </p>
      </div>

      <form class="space-y-4" @submit.prevent="onSubmitManual">
        <BaseInput
          v-model="serverIp"
          v-bind="serverIpAttrs"
          label="IP do Servidor"
          placeholder="Ex: 192.168.1.100"
          :error="errors.serverIp"
        />

        <BaseInput
          v-model="serverPort"
          v-bind="serverPortAttrs"
          type="number"
          label="Porta"
          placeholder="Ex: 8080"
          :error="errors.serverPort"
        />

        <div class="flex gap-3 pt-2">
          <BaseButton variant="secondary" type="button" @click="voltar"> Voltar </BaseButton>
          <BaseButton class="flex-1" type="submit"> Conectar </BaseButton>
        </div>
      </form>
    </template>
  </div>
</template>
