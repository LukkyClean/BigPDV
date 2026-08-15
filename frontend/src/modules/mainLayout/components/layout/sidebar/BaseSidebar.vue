<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useLayoutStore } from '@/modules/mainLayout/store/layout.store';
import { useAuthStore } from '@/shared/stores/auth.store';

import SidebarItem from './SidebarItem.vue';
import CompanyCard from '../../ui/CompanyCard.vue';
import SidebarSectionSkeleton from './SidebarSectionSkeleton.vue';
import AppLogo from '@/shared/components/AppLogo.vue';

import { SIDEBAR_SECTIONS } from '@/modules/mainLayout/constants/layout.constants';
import { computed, onMounted, onUnmounted } from 'vue';
import { useCheckPermission } from '@/modules/mainLayout/composables/useCheckPermission';

const layoutStore = useLayoutStore();
const { activeTab, isMobile, isMobileOpen } = storeToRefs(layoutStore);

const authStore = useAuthStore()
const { userData, isLoading } = storeToRefs(authStore);

const { hasPermission } = useCheckPermission();

const filteredSidebar = computed(() => {
  return SIDEBAR_SECTIONS.map((section) => ({
    ...section,
    options: section.options.filter((opt) => hasPermission(opt.requiredPermission)),
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
          <SidebarItem
            v-for="option in section.options"
            :key="option.id"
            :id="option.id"
            :icon="option.icon"
            :label="option.label"
            :active="activeTab === option.id"
          />
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
