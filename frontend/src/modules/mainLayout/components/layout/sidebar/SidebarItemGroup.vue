<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ChevronDown } from 'lucide-vue-next';

import type { SidebarSubItem } from '@/modules/mainLayout/types/layout.types';
import type { Component } from 'vue';

const props = defineProps<{
  id: string;
  icon: Component;
  label: string;
  children: SidebarSubItem[];
  activeTab: string;
}>();

const router = useRouter();
const isExpanded = ref(false);

const isGroupActive = computed(() =>
  props.activeTab === props.id || props.children.some((c) => c.id === props.activeTab),
);

// Auto-expand quando algum child está ativo
watch(isGroupActive, (active) => {
  if (active) isExpanded.value = true;
}, { immediate: true });

function toggle() {
  isExpanded.value = !isExpanded.value;
}

function handleParentClick() {
  isExpanded.value = true;
  router.push({ name: props.id });
}

function navigateTo(childId: string) {
  router.push({ name: childId });
}
</script>

<template>
  <div>
    <!-- Item pai (navega para a rota pai e expande) -->
    <div
      @click="handleParentClick"
      class="w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group cursor-pointer"
      :class="[
        activeTab === id
          ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/15'
          : isGroupActive
            ? 'bg-brand-primary/10 text-white'
            : 'text-zinc-400 hover:bg-zinc-800 hover:text-white',
      ]"
    >
      <div class="flex items-center space-x-3">
        <component :is="icon" :size="20" />
        <span class="font-medium text-sm">{{ label }}</span>
      </div>
      <button
        type="button"
        @click.stop="toggle"
        class="p-1 -mr-1 rounded hover:bg-white/10 transition-colors"
      >
        <ChevronDown
          :size="16"
          class="transition-transform duration-200"
          :class="isExpanded ? 'rotate-180' : ''"
        />
      </button>
    </div>

    <!-- Children (sub-items) -->
    <Transition name="expand">
      <div v-show="isExpanded" class="ml-4 mt-1 space-y-0.5">
        <button
          v-for="child in children"
          :key="child.id"
          @click="navigateTo(child.id)"
          class="w-full flex items-center px-4 py-2 rounded-lg text-sm transition-all duration-200 cursor-pointer"
          :class="[
            activeTab === child.id
              ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/15'
              : 'text-zinc-500 hover:bg-zinc-800 hover:text-white',
          ]"
        >
          <span class="w-1.5 h-1.5 rounded-full mr-3 shrink-0" :class="[
            activeTab === child.id ? 'bg-white' : 'bg-zinc-600',
          ]" />
          <span class="font-medium">{{ child.label }}</span>
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 200px;
}
</style>
