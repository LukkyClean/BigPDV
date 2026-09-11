<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { Toaster } from 'vue-sonner';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { useAuthStore } from '@/shared/stores/auth.store';
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store';
import { TOKEN_KEY } from '@/api/axios';
import { getDesconectarUrl } from '@/shared/services/licenca.service';
import { aguardarBackend } from '@/shared/services/system/health.service';
import { tentarReconectar } from '@/shared/services/system/reconexao.service';
import {
  tauriDisponivel,
  getConfig,
  isDevMode,
  type StatusBackend,
} from '@/shared/services/system/tauriConfig.service';
import { obterHwid } from '@/shared/services/system/hwid.service';
import AppLoadingScreen from '@/shared/components/AppLoadingScreen.vue';
import { useHealthMonitor } from '@/shared/composables/useHealthMonitor';

// sessionStorage persiste em reloads mas é limpo ao fechar a janela.
// DEVE rodar ANTES de useAuthStore() para que useUserQuery() veja o token já removido.
const SESSION_KEY = 'session_active';
if (!sessionStorage.getItem(SESSION_KEY)) {
  localStorage.removeItem(TOKEN_KEY);
}
sessionStorage.setItem(SESSION_KEY, 'true');

const router = useRouter();
const authStore = useAuthStore();
const networkStore = useNetworkConfigStore();
const { isLoading } = storeToRefs(authStore);
const { statusStartup } = storeToRefs(networkStore);

const appReady = ref(false);
const terminalHwid = ref('');
const detalheStartup = ref<string | null>(null);

useHealthMonitor(appReady);

function handleBeforeUnload() {
  // Dispara desconexão da licença via sendBeacon (fire-and-forget).
  // sendBeacon sobrevive ao unload — garante envio mesmo durante fecho da janela.
  if (terminalHwid.value) {
    navigator.sendBeacon(getDesconectarUrl(terminalHwid.value));
  }
}

let unlistenBackendStatus: UnlistenFn | null = null;
let backendFalhou = false;

/**
 * Enquanto o servidor espera o serviço local, o Tauri emite `backend-status`.
 * Usamos para detalhar a tela de loading e para abortar a espera cedo quando o
 * sidecar falhou (não adianta esperar 120 s por algo que já morreu).
 */
async function ouvirStatusBackend() {
  unlistenBackendStatus = await listen<StatusBackend>('backend-status', (event) => {
    const status = event.payload;
    if (status.modo === 'aguardando_tarefa') {
      detalheStartup.value = 'Aguardando o serviço StartBigServer do Windows responder';
    } else if (status.modo === 'sidecar') {
      detalheStartup.value = 'Serviço iniciado por este aplicativo';
    } else if (status.modo === 'falhou') {
      detalheStartup.value = null;
      backendFalhou = true;
    }
  });
}

async function iniciarComoServidor() {
  networkStore.setPapel('servidor');
  networkStore.setStatusStartup('Iniciando servidor local…');

  const healthy = await aguardarBackend(true, {
    onProgress: (s) => networkStore.setStatusStartup(`Iniciando servidor local… ${s} s`),
    abortar: () => backendFalhou,
  });

  networkStore.setStatusStartup(null);
  networkStore.setOnline(healthy);

  if (!healthy) {
    // Nunca o wizard de "Tipo de máquina": esta máquina JÁ é o servidor. O
    // caminho antigo levava o operador a escolher "Terminal" e apontar para o
    // próprio IP de LAN, que muda com o DHCP.
    networkStore.setSemConexaoBackend(true);
    router.replace({ name: 'erro-conexao' });
  }
}

async function iniciarComoTerminal(serverIp: string, serverPort: number) {
  networkStore.setPapel('terminal');
  networkStore.setConfigAtual(serverIp, serverPort);
  networkStore.setStatusStartup('Conectando ao servidor…');

  const healthy = await aguardarBackend(false);
  if (healthy) {
    networkStore.setOnline(true);
    networkStore.setStatusStartup(null);
    return;
  }

  networkStore.setStatusStartup('Procurando o servidor na rede local…');
  const resultado = await tentarReconectar();
  networkStore.setStatusStartup(null);

  if (resultado.ok) return;

  networkStore.setSemConexaoBackend(true);
  router.replace({ name: 'erro-conexao' });
}

onMounted(async () => {
  // Cachear HWID imediatamente para uso síncrono no beforeunload
  terminalHwid.value = await obterHwid();

  window.addEventListener('beforeunload', handleBeforeUnload);

  if (tauriDisponivel()) {
    await ouvirStatusBackend();
    const config = await getConfig();

    if (!config.configured) {
      networkStore.setNecessitaConfiguracao(true);
      router.replace({ name: 'network-config' });
    } else {
      const devMode = await isDevMode();

      // Em dev mode com role servidor, o backend é iniciado manualmente
      if (devMode && config.is_server) {
        networkStore.setPapel('servidor');
        appReady.value = true;
        return;
      }

      if (config.is_server) {
        await iniciarComoServidor();
      } else {
        await iniciarComoTerminal(config.server_ip, config.server_port);
      }
    }
  }

  appReady.value = true;
});

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload);
  unlistenBackendStatus?.();
});

const isNavigating = ref(false);

router.beforeEach(() => {
  isNavigating.value = true;
});

router.afterEach(() => {
  isNavigating.value = false;
});
</script>

<template>
  <div>
    <Toaster position="top-right" :duration="4000" rich-colors close-button />
    <AppLoadingScreen
      v-if="!appReady || isLoading || isNavigating"
      :mensagem="statusStartup"
      :detalhe="detalheStartup"
    />
    <router-view v-if="appReady" />
  </div>
</template>
