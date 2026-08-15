import { useLayoutStore } from '@/modules/mainLayout/store/layout.store';
import { useAuthStore } from '@/shared/stores/auth.store';
import { verificarLicenca } from '@/shared/services/licenca.service';
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store';
import { storeToRefs } from 'pinia';
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { watch } from 'vue';
import axios from 'axios';

const modules = import.meta.glob('@/modules/**/routes.ts', { eager: true });

const moduleRoutes: RouteRecordRaw[] = Object.values(modules).flatMap((module: any) => {
  return module.default;
});

const routes: RouteRecordRaw[] = [...moduleRoutes];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// ---------------------------------------------------------------------------
// Controle de verificação de licença (throttle de 5 minutos)
// ---------------------------------------------------------------------------
let ultimaVerificacaoLicenca = 0;
const INTERVALO_VERIFICACAO_MS = 5 * 60 * 1000; // 5 minutos

router.beforeEach(async (to) => {
  // -----------------------------------------------------------------------
  // ETAPA 1: Verificação de Licença (antes de qualquer auth check)
  // -----------------------------------------------------------------------
  if (!to.meta.skipLicenseCheck) {
    const agora = Date.now();

    if (agora - ultimaVerificacaoLicenca >= INTERVALO_VERIFICACAO_MS) {
      try {
        await verificarLicenca();
        ultimaVerificacaoLicenca = agora;
      } catch (error) {
        if (axios.isAxiosError(error) && error.response) {
          const status = error.response.status;

          if (status === 403) {
            const detail = error.response.data?.detail || error.response.data || {};
            const codigo = detail.codigo || 'ERRO_DESCONHECIDO';
            const mensagem = detail.mensagem || 'Erro na verificação da licença.';

            return {
              name: 'licenca.erro',
              query: { codigo, mensagem },
            };
          }

          // 404 = sem licença = sistema não inicializado → sign-in
          if (status === 404) {
            return { name: 'sign-in' };
          }
        }
        // Erro de rede (backend não pronto) — permitir navegação
      }
    }
  }

  // -----------------------------------------------------------------------
  // ETAPA 2: Verificação de Autenticação
  // -----------------------------------------------------------------------
  // Guard de rede: bloqueia navegação se config de rede é necessária
  const networkStore = useNetworkConfigStore();
  if (networkStore.necessitaConfiguracao && to.name !== 'network-config') {
    return { name: 'network-config' };
  }

  // Guard de conexão: bloqueia terminal sem conexão ao servidor
  if (networkStore.erroConexaoTerminal && to.name !== 'erro-conexao' && to.name !== 'network-config') {
    return { name: 'erro-conexao' };
  }

  const authStore = useAuthStore();
  const { isAuthenticated, isLoading } = storeToRefs(authStore);

  if (to.meta.requiresAuth) {
    // Se a store ainda está carregando, PAUSA o router
    if (isLoading.value) {
      await new Promise<void>((resolve) => {
        const unwatch = watch(isLoading, (loading) => {
          if (!loading) {
            unwatch();
            resolve();
          }
        });
      });
    }

    // Verifica se está autenticado
    if (!isAuthenticated.value) {
      return {
        name: 'auth.user',
        query: { redirect: to.fullPath },
      };
    }
  }

  // -----------------------------------------------------------------------
  // ETAPA 3: Módulos que o segmento da loja não usa
  // -----------------------------------------------------------------------
  // Roda DEPOIS da autenticação de propósito: a resposta depende de
  // `userData.empresa`, que só existe com o usuário carregado. Antes disso
  // `usa_ordem_servico` seria indefinido e cairia no padrão (tem OS) — que é
  // seguro, mas deixaria a rota passar.
  //
  // Esconder o item do menu não basta: sem isto, digitar /servicos na barra de
  // endereço abriria a tela de OS numa loja que não tem o módulo.
  if (to.meta.exigeOrdemServico) {
    const authStore = useAuthStore();
    const usaOrdemServico = authStore.userData?.empresa?.usa_ordem_servico ?? true;
    if (!usaOrdemServico) {
      return { name: 'home' };
    }
  }
});

router.afterEach((to) => {
  const layoutStore = useLayoutStore();
  layoutStore.updatePageInfo(to);
});

export default router;
