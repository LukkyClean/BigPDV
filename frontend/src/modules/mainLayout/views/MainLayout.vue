<script setup lang="ts">
import { Zap, ShoppingCart, FileText, Package, Wrench } from 'lucide-vue-next';
import { useMagicKeys, whenever } from '@vueuse/core'
import { storeToRefs } from 'pinia';

import BaseSidebar from '../components/layout/sidebar/BaseSidebar.vue';
import BaseHeader from '../components/layout/BaseHeader.vue';
import QuickActions from '../components/ui/QuickActions.vue';

import CustomerFormModal from '@/modules/customers/components/modal/CustomerFormModal.vue';
import ProductModal from '@/modules/products/inventory/components/ProductModal.vue';
import ServicoFormModal from '@/modules/order-service/servicos/components/ServicoFormModal.vue';
import CustomerSearchModal from '@/modules/sales/components/CustomerSearchModal.vue';
import SaleModal from '@/modules/sales/components/SaleModal.vue';
import OSClienteSearchModal from '@/modules/order-service/ordens/components/OSClienteSearchModal.vue';
import OSFormModal from '@/modules/order-service/ordens/components/OSFormModal.vue';
import OSObjetoSelectModal from '@/modules/order-service/ordens/components/form/OSObjetoSelectModal.vue';
import OSCreditoAlertModal from '@/modules/order-service/ordens/components/OSCreditoAlertModal.vue';

import { useLayoutStore } from '../store/layout.store';
import { useSettingsStore } from '@/shared/stores/settings.store';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { sincronizarServidorImpressao } from '@/shared/services/impressao.service';
import { useNotificacoesStore } from '@/shared/stores/notificacoes.store';
import { useQuery } from '@tanstack/vue-query';
import { getOsAbandono, getOsAtrasadas } from '@/modules/order-service/ordens/services/orderServiceGet.service';
import { getComunicados } from '../services/comunicado.service';
import { watch, onMounted, computed } from 'vue';
import MinhaContaModal from '@/modules/minha-conta/components/MinhaContaModal.vue';
import ConfiguracoesModal from '@/modules/configuracoes/components/ConfiguracoesModal.vue';
import { useCustomerSearchModal } from '@/modules/sales/composables/flows/useCustomerSearchModal';
import { useOSCreateFlow } from '@/modules/order-service/ordens/composables/useOSCreateFlow';
import { useProductModal } from '@/modules/products/inventory/composables/useProductModal.ts';
import { useServicoModal } from '@/modules/order-service/servicos/composables/useServicoModal';

const layoutStore = useLayoutStore();
const settingsStore = useSettingsStore();
const configuracoesStore = useConfiguracoesStore();
const impressaoStore = useImpressaoStore();
const notificacoesStore = useNotificacoesStore();
const { isMobile, isMobileOpen, isQuickOpen, isSettingsOpen, isMinhaContaOpen, isConfiguracoesOpen, secaoConfiguracoesAtiva } = storeToRefs(layoutStore);

const { data: osAbandonoData } = useQuery({
  queryKey: ['os-abandono'],
  queryFn: getOsAbandono,
  refetchInterval: 1000 * 60 * 15,
});
watch(osAbandonoData, (lista) => {
  if (lista) notificacoesStore.setOsAbandono(lista);
}, { immediate: true });

const { data: osAtrasadasData } = useQuery({
  queryKey: ['os-atrasadas'],
  queryFn: getOsAtrasadas,
  refetchInterval: 1000 * 60 * 15,
});
watch(osAtrasadasData, (lista) => {
  if (lista) notificacoesStore.setOsAtrasadas(lista);
}, { immediate: true });

const { data: comunicadosData } = useQuery({
  queryKey: ['comunicados'],
  queryFn: getComunicados,
  refetchInterval: 1000 * 60 * 5,
});
watch(comunicadosData, (lista) => {
  if (lista) notificacoesStore.setComunicados(lista);
}, { immediate: true });

onMounted(() => {
  settingsStore.init();
  configuracoesStore.carregarConfiguracoes();
  impressaoStore.carregar();
  // Religa o servidor de impressão na LAN se este PC compartilha a térmica
  sincronizarServidorImpressao(impressaoStore.config).catch((e) => {
    console.error('[Impressão] Falha ao iniciar servidor de impressão:', e);
  });
});

const { openCustomerModal } = useCustomerSearchModal();
const {
  isClienteSearchOpen,
  isFormModalOpen,
  isObjetoSelectOpen,
  isCreditAlertOpen,
  selectedCliente,
  selectedOS,
  objetosHistoricoFlow,
  selectedObjeto,
  autoOpenReopen,
  autoUsarCredito,
  openNovaOS,
  handleClienteSelected,
  handleCreditoUsado,
  handleCreditoIgnorado,
  handleObjetoSelectedFlow,
  skipObjetoSelectFlow,
  handleChangeCliente,
  closeClienteSearch,
  closeFormModal,
} = useOSCreateFlow();

const nomeCreditoCliente = computed(() => {
  const c = selectedCliente.value as { tipo?: string; nome?: string; nome_fantasia?: string; razao_social?: string } | null;
  if (!c) return '';
  if (c.tipo === 'PF') return c.nome || '';
  return c.nome_fantasia || c.razao_social || '';
});

const valorCreditoCliente = computed(() =>
  (selectedCliente.value as { saldo_credito?: number } | null)?.saldo_credito ?? 0
);
const { openCreateModal: openProductCreate } = useProductModal();
const { openCreateModal: openServicoCreate } = useServicoModal();

const quickActions: import('@/modules/home/types/dashboard.types').QuickActionItem[] = [
  { id: 'nova-venda', icon: ShoppingCart, label: 'Criar Venda', variant: 'primary', action: () => openCustomerModal() },
  { id: 'nova-os', icon: FileText, label: 'Criar OS', variant: 'primary', action: () => openNovaOS() },
  { id: 'novo-produto', icon: Package, label: 'Criar Produto', variant: 'secondary', action: () => openProductCreate() },
  { id: 'novo-servico', icon: Wrench, label: 'Criar Serviço', variant: 'secondary', action: () => openServicoCreate() },
];

const { Ctrl_K } = useMagicKeys();

whenever(Ctrl_K, () => {
  layoutStore.toggleQuick();
});
</script>

<template>
  <div class="flex h-screen bg-brand-off-white overflow-hidden">
    <Transition name="fade">
      <div
        v-if="(isMobile && isMobileOpen)"
        class="fixed inset-0 bg-black/50 z-40 lg:hidden"
        @click="layoutStore.closeSidebar"
      />
    </Transition>

      <div
        v-if="isQuickOpen"
        class="fixed inset-0 bg-transparent z-40"
        @click="layoutStore.toggleQuick"
      />

      <div
        v-if="isSettingsOpen"
        class="fixed inset-0 bg-transparent z-40"
        @click="layoutStore.closeSettings"
      />

    <BaseSidebar />

    <main class="relative flex-1 overflow-y-auto flex flex-col min-w-0">
      <BaseHeader />
      <div class="flex-1 overflow-y-auto">
        <router-view />
      </div>

      <Transition name="pop" mode="out-in">
        <button
          v-if="!isQuickOpen"
          class="fixed z-10 right-5 bottom-5 text-white bg-brand-primary p-3 rounded-full cursor-pointer shadow-lg hover:bg-brand-primary/90 transition-colors"
          @click="layoutStore.toggleQuick"
        >
          <Zap :size="24" fill="white" />
        </button>

        <div v-else class="fixed bottom-5 right-5 z-50">
          <QuickActions @clicked="layoutStore.toggleQuick" :actions="quickActions" />
        </div>
      </Transition>
    </main>

    <!-- Modal Minha Conta -->
    <MinhaContaModal
      :isOpen="isMinhaContaOpen"
      @close="layoutStore.closeMinhaConta"
    />

    <!-- Modal Configurações Gerais -->
    <ConfiguracoesModal
      :isOpen="isConfiguracoesOpen"
      :secao-inicial="(secaoConfiguracoesAtiva as any)"
      @close="layoutStore.closeConfiguracoes"
    />

    <!-- Modais globais (disponíveis em todo o sistema) -->
    <CustomerFormModal />
    <ProductModal />
    <ServicoFormModal />
    <CustomerSearchModal />
    <SaleModal />

    <OSClienteSearchModal
      :is-open="isClienteSearchOpen"
      @close="closeClienteSearch"
      @select-cliente="handleClienteSelected"
    />

    <OSCreditoAlertModal
      :is-open="isCreditAlertOpen"
      :valor-credito="valorCreditoCliente"
      :nome-cliente="nomeCreditoCliente"
      @usar="handleCreditoUsado"
      @fechar="handleCreditoIgnorado"
    />

    <OSObjetoSelectModal
      :is-open="isObjetoSelectOpen"
      :objetos="objetosHistoricoFlow"
      @close="skipObjetoSelectFlow"
      @select="handleObjetoSelectedFlow"
    />

    <OSFormModal
      :is-open="isFormModalOpen"
      :ordem-servico="selectedOS"
      :selected-cliente="selectedCliente"
      :initial-objeto="selectedObjeto"
      :auto-usar-credito="autoUsarCredito"
      :auto-open-reopen="autoOpenReopen"
      @close="closeFormModal"
      @change-cliente="handleChangeCliente"
    />
  </div>
</template>

<style scoped>
/* Transição existente do Overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* --- NOVA TRANSIÇÃO: Quick Actions (Efeito Pop/Scale) --- */
.pop-enter-active,
.pop-leave-active {
  /* O cubic-bezier dá um efeito de elástico/salto sutil */
  transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: scale(0.5); /* Começa/Termina pequeno */
}
</style>
