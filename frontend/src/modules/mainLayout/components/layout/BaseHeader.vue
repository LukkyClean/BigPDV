<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Bell, Menu, ChevronDown, User } from 'lucide-vue-next';
import { useLayoutStore } from '../../store/layout.store';
import { storeToRefs } from 'pinia';
import SettingsMenu from '../ui/SettingsMenu.vue';
import NotificacoesPanel from '../ui/NotificacoesPanel.vue';
import LicencaStatusBadge from '../ui/LicencaStatusBadge.vue';
import { useNotificacoesStore } from '@/shared/stores/notificacoes.store';
import { useAuthStore } from '@/shared/stores/auth.store';
import { onClickOutside } from '@vueuse/core';
import { useQueryClient } from '@tanstack/vue-query';
import { getImageUrl } from '@/shared/utils/print.utils';

const layoutStore = useLayoutStore();
const { pageTitle, pageSubtitle, isMobile, isSettingsOpen } = storeToRefs(layoutStore);
const notificacoesStore = useNotificacoesStore();
const authStore = useAuthStore();
const { userData } = storeToRefs(authStore);

const settingsButtonRef = ref<HTMLButtonElement | null>(null);
const notifButtonRef = ref<HTMLButtonElement | null>(null);
const notifPanelRef = ref<HTMLElement | null>(null);
const isNotifOpen = ref(false);
const queryClient = useQueryClient();

// O alvo é o painel; o botão entra em `ignore` para o clique nele apenas alternar
// (senão fecharia aqui e reabriria no @click do próprio botão).
// Passar um array como alvo quebra: o `unrefElement` não devolve um Element, o
// VueUse cai no `hasMultipleRoots`, lê `vm.$.subTree` de um array e lança —
// antes do handler, então o painel nunca fechava ao clicar fora.
onClickOutside(notifPanelRef, () => { isNotifOpen.value = false; }, {
  ignore: [notifButtonRef],
});

watch(isNotifOpen, (open) => {
  if (open) {
    queryClient.invalidateQueries({ queryKey: ['comunicados'] });
    queryClient.invalidateQueries({ queryKey: ['os-atrasadas'] });
    queryClient.invalidateQueries({ queryKey: ['os-abandono'] });
  }
});

const menuStyle = computed((): Record<string, string> => {
  if (!settingsButtonRef.value) return {};
  const rect = settingsButtonRef.value.getBoundingClientRect();
  return {
    top: `${rect.bottom + 8}px`,
    right: `${window.innerWidth - rect.right}px`,
  };
});

const notifStyle = computed((): Record<string, string> => {
  if (!notifButtonRef.value) return {};
  const rect = notifButtonRef.value.getBoundingClientRect();
  return {
    top: `${rect.bottom + 8}px`,
    right: `${window.innerWidth - rect.right}px`,
  };
});
</script>

<template>
  <header
    class="w-full h-16 md:h-20 bg-white border-b border-zinc-200 px-4 md:px-8 flex items-center justify-between sticky top-0 z-30"
  >
    <!-- Left Section: Hamburger + Title -->
    <div class="flex items-center gap-3 md:gap-4">
      <!-- Hamburger Menu (Mobile Only) -->
      <button
        v-if="isMobile"
        class="p-2 -ml-2 text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors"
        @click="layoutStore.toggleSidebar"
        aria-label="Abrir menu"
      >
        <Menu :size="24" />
      </button>

      <!-- Page Title -->
      <div class="flex flex-col">
        <h1 class="text-lg md:text-2xl text-brand-primary font-extrabold leading-tight">
          {{ pageTitle }}
        </h1>
        <p class="text-[10px] md:text-xs text-zinc-400 font-medium hidden sm:block">
          {{ pageSubtitle }}
        </p>
      </div>
    </div>

    <!-- Right Section: Actions -->
    <div class="flex flex-1 items-center justify-end xl:max-w-2xl lg:max-w-md gap-2 md:gap-4">
      <!-- Badge de Status da Licença -->
      <LicencaStatusBadge />

      <!-- Notifications -->
      <button
        ref="notifButtonRef"
        class="relative p-2 text-zinc-500 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
        :class="isNotifOpen && 'bg-zinc-100 text-zinc-800'"
        aria-label="Notificações"
        @click="isNotifOpen = !isNotifOpen"
      >
        <Bell :size="20" />
        <span
          v-if="notificacoesStore.totalNaoLidas > 0"
          class="absolute top-1 right-1 min-w-4 h-4 px-0.5 bg-red-500 border-2 border-white rounded-full flex items-center justify-center text-[9px] font-bold text-white"
        >{{ notificacoesStore.totalNaoLidas > 9 ? '9+' : notificacoesStore.totalNaoLidas }}</span>
      </button>

      <!-- User Avatar Button -->
      <button
        ref="settingsButtonRef"
        @click="layoutStore.toggleSettings"
        :class="[
          'flex items-center gap-1.5 pl-1 pr-2 py-1 rounded-xl transition-colors cursor-pointer',
          isSettingsOpen ? 'bg-zinc-100' : 'hover:bg-zinc-100',
        ]"
        aria-label="Configurações"
      >
        <div class="w-8 h-8 rounded-lg bg-brand-primary flex items-end justify-center overflow-hidden shrink-0">
          <img
            v-if="userData?.url_perfil"
            :src="getImageUrl(userData.url_perfil) ?? ''"
            alt="Foto do usuário"
            class="w-full h-full object-cover"
          />
          <User v-else :size="22" class="text-white" />
        </div>
        <ChevronDown
          :size="14"
          class="text-zinc-400 transition-transform duration-200"
          :class="isSettingsOpen && 'rotate-180'"
        />
      </button>
    </div>
  </header>

  <!-- Menus renderizados no body via Teleport para escapar do z-index do header -->
  <Teleport to="body">
    <div ref="notifPanelRef">
      <Transition name="dropdown">
        <NotificacoesPanel v-if="isNotifOpen" :style="notifStyle" @close="isNotifOpen = false" />
      </Transition>
    </div>
    <Transition name="dropdown">
      <SettingsMenu v-if="isSettingsOpen" :style="menuStyle" />
    </Transition>
  </Teleport>
</template>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
</style>
