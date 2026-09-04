import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { RouteLocationNormalized, useRoute } from 'vue-router';

import { SidebarLabelOptions } from '../types/layout.types';

export const useLayoutStore = defineStore('layout', () => {
  //Constantes
  const MOBILE_BREAKPOINT = 768;

  //Utilitarios
  const route = useRoute();

  //Menu mobile
  const isMobileOpen = ref(false);
  const isMobile = ref(false);

  const isOpen = computed(() => !isMobile.value || isMobileOpen.value);

  function checkIsMobile(): void {
    isMobile.value = window.innerWidth < MOBILE_BREAKPOINT;

    if (!isMobile.value && isMobileOpen.value) {
      isMobileOpen.value = false;
    }
  }

  //Menu geral
  const pageTitle = ref<SidebarLabelOptions>('Início');
  const pageSubtitle = ref<string>('');
  const activeTab = ref<string>('');
  
  const isQuickOpen = ref<boolean>(false);
  const isSettingsOpen = ref<boolean>(false);
  const isMinhaContaOpen = ref<boolean>(false);
  const isConfiguracoesOpen = ref<boolean>(false);
  const isRenovarAssinaturaOpen = ref<boolean>(false);
  const secaoConfiguracoesAtiva = ref<string>('regras-de-vendas');

  //Listener
  function init() {
    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);
  }

  function close() {
    window.removeEventListener('resize', checkIsMobile);
  }

   //Metodos
  function updatePageInfo(route: RouteLocationNormalized) {
    const { meta } = route;
    pageTitle.value = meta.title as SidebarLabelOptions;
    pageSubtitle.value = meta.subtitle || '';
    activeTab.value = meta.tabId || '';
  }

  function closeSidebar() {
    isMobileOpen.value = false;
  }

  function toggleSidebar() {
    if (isMobile) {
      isMobileOpen.value = !isMobileOpen.value;
    }
  }

  function toggleQuick() {
    isQuickOpen.value = !isQuickOpen.value;
  }

  function toggleSettings() {
    isSettingsOpen.value = !isSettingsOpen.value;
  }

  function closeSettings() {
    isSettingsOpen.value = false;
  }

  function openMinhaConta() {
    isSettingsOpen.value = false;
    isMinhaContaOpen.value = true;
  }

  function closeMinhaConta() {
    isMinhaContaOpen.value = false;
  }

  function openConfiguracoes(secao: string = 'regras-de-vendas') {
    isSettingsOpen.value = false;
    secaoConfiguracoesAtiva.value = secao;
    isConfiguracoesOpen.value = true;
  }

  function closeConfiguracoes() {
    isConfiguracoesOpen.value = false;
  }

  function openRenovarAssinatura() {
    isSettingsOpen.value = false;
    isRenovarAssinaturaOpen.value = true;
  }

  function closeRenovarAssinatura() {
    isRenovarAssinaturaOpen.value = false;
  }

  watch(
    () => route.path,
    () => {
      isSettingsOpen.value = false;
      isQuickOpen.value = false;
      if (isMobile.value && isMobileOpen.value) {
        closeSidebar();
      }
    },
  );

  return {
    // Refs
    pageTitle,
    pageSubtitle,
    activeTab,
    isMobile,
    isMobileOpen,
    isOpen,
    isQuickOpen,
    isSettingsOpen,
    isMinhaContaOpen,
    isConfiguracoesOpen,
    isRenovarAssinaturaOpen,
    secaoConfiguracoesAtiva,

    //Metodos
    updatePageInfo,
    toggleSidebar,
    closeSidebar,
    toggleQuick,
    toggleSettings,
    closeSettings,
    openMinhaConta,
    closeMinhaConta,
    openConfiguracoes,
    closeConfiguracoes,
    openRenovarAssinatura,
    closeRenovarAssinatura,

    // Listeners
    init,
    close,
  };
});
