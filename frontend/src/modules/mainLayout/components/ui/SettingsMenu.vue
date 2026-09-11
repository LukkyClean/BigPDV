<script setup lang="ts">
import { storeToRefs } from 'pinia';
import {
  User,
  Settings,
  Printer,
  MessageCircle,
  HelpCircle,
  BookOpen,
  Wifi,
  LogOut,
  RefreshCw,
  ChevronRight,
} from 'lucide-vue-next';

import { useAuthStore } from '@/shared/stores/auth.store';
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store';
import { useAppNavigation } from '@/shared/composables/useAppNavigation';
import { useLayoutStore } from '../../store/layout.store';
import { openUrl } from '@tauri-apps/plugin-opener';
import { LINKS } from '@/shared/config/links';

import { getImageUrl } from '@/shared/utils/print.utils';

const authStore = useAuthStore();
const layoutStore = useLayoutStore();

const networkStore = useNetworkConfigStore();

const { userData } = storeToRefs(authStore);
const { online, papel } = storeToRefs(networkStore);
const { logoutAndRedirect } = useAppNavigation();

function abrirMinhaConta() {
  layoutStore.openMinhaConta();
}

function abrirConfiguracoes() {
  layoutStore.openConfiguracoes();
}
</script>

<template>
  <div class="fixed w-64 z-50">
    <!-- Seta de conexão com o ícone -->
    <div class="absolute -top-1.5 right-3.5 w-3 h-3 bg-white border-l border-t border-zinc-200 rotate-45 z-10" />

    <!-- Conteúdo do menu -->
    <div class="bg-white border border-zinc-200 rounded-xl shadow-lg overflow-y-auto no-scrollbar" style="max-height: 450px;">

      <!-- USUÁRIO -->
      <div class="px-2.5 pt-2.5 pb-2 border-b border-zinc-100">
        <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest px-1 mb-1.5">
          Usuário
        </p>

        <div class="flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg bg-zinc-50">
          <div
            class="w-8 h-8 bg-brand-primary p-0.5 rounded-lg flex items-end justify-center shrink-0 overflow-hidden"
          >
            <img
              v-if="userData?.url_perfil"
              :src="getImageUrl(userData.url_perfil) ?? ''"
              alt="Foto do usuário"
              class="w-full h-full object-cover rounded-lg"
            />
            <User v-else :size="22" class="text-white" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-zinc-800 truncate">{{ userData?.nome ?? '—' }}</p>
            <p class="text-[10px] text-zinc-400 leading-tight">{{ userData?.cargo?.nome ?? '—' }}</p>
          </div>
        </div>

        <button
          @click="abrirMinhaConta"
          class="w-full mt-1.5 text-xs text-zinc-600 bg-zinc-100 hover:bg-zinc-200 transition-colors rounded-md py-1.5 px-3 text-center cursor-pointer"
        >
          Meus Dados / Minha Conta
        </button>
      </div>

<!-- PAINEL DO SISTEMA -->
      <div class="px-2.5 py-2 border-b border-zinc-100">
        <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest px-1 mb-1">
          Painel do Sistema
        </p>

        <button
          class="w-full flex items-center justify-between px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          @click="abrirConfiguracoes"
        >
          <div class="flex items-center gap-2">
            <Settings :size="14" class="text-zinc-500" />
            <span class="text-xs text-zinc-700">Configurações Gerais</span>
          </div>
          <ChevronRight :size="12" class="text-zinc-400" />
        </button>

        <button
          class="w-full flex items-center justify-between px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          @click="layoutStore.openConfiguracoes('impressao')"
        >
          <div class="flex items-center gap-2">
            <Printer :size="14" class="text-zinc-500" />
            <span class="text-xs text-zinc-700">Ajustar Impressão</span>
          </div>
          <ChevronRight :size="12" class="text-zinc-400" />
        </button>
      </div>

      <!-- SUPORTE -->
      <div class="px-2.5 py-2 border-b border-zinc-100">
        <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest px-1 mb-1">
          Suporte
        </p>

        <button
          class="w-full flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          @click="openUrl(LINKS.whatsapp)"
        >
          <MessageCircle :size="14" class="text-zinc-500" />
          <span class="text-xs text-zinc-700">Falar com o Suporte</span>
        </button>

        <button
          class="w-full flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          @click="openUrl(LINKS.site)"
        >
          <HelpCircle :size="14" class="text-zinc-500" />
          <span class="text-xs text-zinc-700">Central de Ajuda</span>
        </button>

        <button
          class="w-full flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          @click="openUrl(LINKS.youtube)"
        >
          <BookOpen :size="14" class="text-zinc-500" />
          <span class="text-xs text-zinc-700">Tutoriais</span>
        </button>
      </div>

      <!-- AÇÕES GERAIS -->
      <div class="px-2.5 pt-2 pb-2.5">
        <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest px-1 mb-1">
          Ações Gerais
        </p>

        <button
          class="w-full flex items-center gap-2 px-1.5 py-1.5 rounded-lg opacity-40 cursor-not-allowed"
          disabled
        >
          <RefreshCw :size="14" class="text-zinc-500" />
          <span class="text-xs text-zinc-700">Renovar Assinatura</span>
        </button>

        <!-- Status real do backend (alimentado pelo useHealthMonitor); abre o diagnóstico -->
        <button
          class="w-full flex items-center justify-between px-1.5 py-1.5 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
          title="Diagnóstico de conexão"
          @click="layoutStore.openConfiguracoes('rede')"
        >
          <div class="flex items-center gap-1.5">
            <Wifi
              :size="14"
              :class="online === null ? 'text-zinc-400' : online ? 'text-emerald-500' : 'text-red-500'"
            />
            <span class="text-xs text-zinc-500">{{ papel === 'servidor' ? 'Servidor:' : 'Conexão:' }}</span>
            <span
              class="text-xs font-medium"
              :class="online === null ? 'text-zinc-400' : online ? 'text-emerald-500' : 'text-red-500'"
            >
              {{ online === null ? 'verificando' : online ? 'Online' : 'Sem resposta' }}
            </span>
          </div>
          <ChevronRight :size="12" class="text-zinc-400" />
        </button>

        <button
          @click="logoutAndRedirect"
          class="w-full mt-1 flex items-center justify-center gap-1.5 bg-red-50 hover:bg-red-100 text-red-500 hover:text-red-600 transition-colors rounded-lg py-2 px-3 font-medium text-xs cursor-pointer"
        >
          <LogOut :size="14" />
          Sair do Sistema
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.no-scrollbar {
  scrollbar-width: none;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
</style>
