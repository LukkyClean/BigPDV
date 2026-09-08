<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useLayoutStore } from '@/modules/mainLayout/store/layout.store';
import { useAuthStore } from '@/shared/stores/auth.store';

import SidebarItem from './SidebarItem.vue';
import SidebarItemGroup from './SidebarItemGroup.vue';
import type { SidebarSubItemResolvido } from './SidebarItemGroup.vue';
import type { SidebarSubItem } from '@/modules/mainLayout/types/layout.types';
import CompanyCard from '../../ui/CompanyCard.vue';
import SidebarSectionSkeleton from './SidebarSectionSkeleton.vue';
import AppLogo from '@/shared/components/AppLogo.vue';

import { SIDEBAR_SECTIONS } from '@/modules/mainLayout/constants/layout.constants';
import { computed, onMounted, onUnmounted } from 'vue';
import { useCheckPermission } from '@/modules/mainLayout/composables/useCheckPermission';
import { useOrdemServico } from '@/shared/composables/useOrdemServico';
import { useModulosStore } from '@/shared/stores/modulos.store';

const layoutStore = useLayoutStore();
const { activeTab, isMobile, isMobileOpen } = storeToRefs(layoutStore);

const authStore = useAuthStore()
const { userData, isLoading } = storeToRefs(authStore);

const { hasPermission } = useCheckPermission();
const { usaOrdemServico } = useOrdemServico();
const modulosStore = useModulosStore();

/**
 * Sub-itens que este usuário deve enxergar, já resolvidos.
 *
 * As duas travas tratam o filho de formas DIFERENTES, e é de propósito:
 *
 * - Sem PERMISSÃO o item some. Quem não pode ver a folha de pagamento também
 *   não precisa saber que a tela existe.
 * - Sem MÓDULO o item fica, com cadeado. A loja já está dentro do módulo; o
 *   sub-item do plano superior é justamente onde o upgrade se vende, e sumir
 *   com ele viraria "o sistema perdeu uma tela" no suporte.
 *
 * (No item PAI o módulo ausente esconde — ver `requiredModule` em
 * layout.types.ts. Anunciar um módulo que a loja não comprou é outra conversa,
 * e essa mora no painel de vendas.)
 */
function resolverFilhos(filhos: SidebarSubItem[]): SidebarSubItemResolvido[] {
  return filhos
    .filter((filho) => hasPermission(filho.requiredPermission))
    .map((filho) => ({
      ...filho,
      bloqueado: !!filho.requiredModule && !modulosStore.temModulo(filho.requiredModule),
    }));
}

const filteredSidebar = computed(() => {
  return SIDEBAR_SECTIONS.map((section) => ({
    ...section,
    options: section.options
      .filter((opt) => {
        // Loja sem Ordem de Serviço não vê o módulo. Único item gateado por
        // segmento aqui; todo o resto continua sendo só permissão.
        if (opt.id === 'services' && !usaOrdemServico.value) return false;
        // Recurso fora do plano SOME -- diferente de módulo não contratado,
        // que fica com cadeado. Ver `featureFlag` em layout.types.ts para
        // quando usar cada um.
        if (opt.featureFlag && !opt.featureFlag()) return false;
        return hasPermission(opt.requiredPermission);
      })
      .map((opt) => ({
        ...opt,
        children: opt.children ? resolverFilhos(opt.children) : undefined,
        // Módulo não contratado TRAVA, não some — nem para o dono. Sumir vira
        // "o sistema perdeu uma tela" no suporte; o cadeado diz a verdade e é
        // onde a venda do upgrade acontece. Mesma razão que o backend já dá em
        // core/modulos.py para responder 403 e não 404.
        //
        // Grupo não trava no pai: quem carrega o cadeado são os filhos, cada um
        // com o seu próprio módulo — e num grupo eles podem ser de planos
        // diferentes, como Contas a Pagar e Fluxo de Caixa.
        bloqueado:
          !opt.children &&
          !!opt.requiredModule &&
          !modulosStore.temModulo(opt.requiredModule),
      }))
      // Grupo que perdeu todos os filhos por permissão vira um pai que abre e
      // não mostra nada. Some junto.
      .filter((opt) => !opt.children || opt.children.length > 0),
  })).filter((section) => section.options.length > 0);
});

onMounted(() => {
  layoutStore.init();
});

onUnmounted(() => {
  layoutStore.close();
});
</script>

<template>
  <Transition name="slide">
    <aside
      v-show="!isMobile || isMobileOpen"
      :class="[
        'w-72 bg-brand-action text-white flex flex-col h-full border-r border-zinc-800 select-none',
        'transition-transform duration-300 ease-out',
        isMobile ? 'fixed inset-y-0 left-0 z-50' : 'relative',
      ]"
    >
      <!-- Company Header -->
      <div class="p-6">
        <CompanyCard
          :company-name="userData?.empresa?.nome_fantasia || userData?.empresa?.razao_social || 'Error'"
          :image-url="userData?.empresa?.url_logo"
          :status="userData?.empresa?.ativo ?? false"
          :is-loading="isLoading"
        />
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 space-y-4 mt-2 mb-2 overflow-y-auto custom-scrollbar">
        <SidebarSectionSkeleton v-if="isLoading" />

        <div v-else v-for="(section, index) in filteredSidebar" :key="index" class="space-y-1">
          <p class="px-4 text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-2">
            {{ section.title }}
          </p>
          <template v-for="option in section.options" :key="option.id">
            <SidebarItemGroup
              v-if="option.children?.length"
              :icon="option.icon"
              :label="option.label"
              :children="option.children"
              :active-tab="activeTab"
            />
            <SidebarItem
              v-else
              :id="option.id"
              :icon="option.icon"
              :label="option.label"
              :active="activeTab === option.id"
              :bloqueado="option.bloqueado"
            />
          </template>
        </div>
      </nav>

      <!-- Logo rodapé -->
      <div class="p-4 mt-auto border-t border-zinc-800/60 flex items-center justify-center">
        <AppLogo class="h-10 w-auto max-w-full object-contain opacity-80" />
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease-out;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
