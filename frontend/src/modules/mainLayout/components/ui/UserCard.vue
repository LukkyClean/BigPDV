<script setup lang="ts">
import { useAppNavigation } from '@/shared/composables/useAppNavigation';

import { LogOut, User } from 'lucide-vue-next';

import StatusPulse from '../icons/StatusPulse.vue';
import { getImageUrl } from '@/shared/utils/print.utils';

defineProps<{
  userName?: string;
  userCargo?: string;
  imageUrl?: string;
  status?: boolean;
  isLoading: boolean;
}>();

const { logoutAndRedirect } = useAppNavigation();
</script>

<template>
  <div
    v-if="isLoading"
    class="flex items-center space-x-3 p-3 rounded-2xl bg-zinc-900 animate-pulse select-none cursor-wait"
  >
    <div class="w-10 h-10 bg-zinc-800 rounded-xl shrink-0"></div>

    <div class="flex-1 min-w-0 space-y-2">
      <div class="h-4 bg-zinc-800 rounded w-3/5"></div>
      <div class="h-3 bg-zinc-800 rounded w-2/5"></div>
    </div>
  </div>
  
  <div
    v-else
    class="flex items-center space-x-3 p-3 rounded-2xl bg-zinc-900 hover:bg-zinc-800 transition-colors group"
  >
    <div class="flex items-end justify-center w-10 h-10 bg-brand-primary p-0.5 rounded-xl">
      <img
        v-if="imageUrl"
        :src="getImageUrl(imageUrl) ?? ''"
        alt="Foto do usuário"
        class="w-full h-full object-cover rounded-xl"
      />
      <User v-else :size="30" class="text-white" />
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-semibold truncate group-hover:text-zinc-300 transition-colors">
        {{ userName }}
      </p>
      <div class="flex items-center gap-2">
        <StatusPulse :status="status ?? false" />
        <p class="text-xs text-zinc-500 font-medium">
          {{ userCargo }}
        </p>
      </div>
    </div>
    <button
      class="p-2 rounded-lg hover:bg-zinc-700 transition-colors group/logout cursor-pointer"
      @click.stop="logoutAndRedirect()"
      aria-label="Sair da conta"
    >
      <LogOut :size="16" class="text-zinc-600 group-hover/logout:text-red-400 transition-colors" />
    </button>
  </div>
</template>
