<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Lock } from 'lucide-vue-next';

import { SidebarLabelOptions } from '@/modules/mainLayout/types/layout.types';
import type { Component } from 'vue';

const props = defineProps<{
  id: string;
  icon: Component;
  label: SidebarLabelOptions;
  active: boolean;
  /** Módulo não contratado: aparece travado em vez de sumir. */
  bloqueado?: boolean;
}>();

const router = useRouter();

function abrir() {
  // Travado não navega. O guard do router devolveria para a home de qualquer
  // forma, e um clique que pisca e volta parece defeito -- o cadeado já diz o
  // que está acontecendo.
  if (props.bloqueado) return;
  router.push({ name: props.id });
}
</script>
<template>
  <button
    type="button"
    :disabled="bloqueado"
    :title="bloqueado ? 'Não incluído no seu plano. Fale com o suporte.' : undefined"
    @click="abrir"
    class="w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group"
    :class="[
      bloqueado
        ? 'text-zinc-600 cursor-not-allowed'
        : active
          ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/15 cursor-pointer'
          : 'text-zinc-400 hover:bg-zinc-800 hover:text-white cursor-pointer',
    ]"
  >
    <component :is="icon" :size="20" />
    <span class="font-medium text-sm">{{ label }}</span>
    <Lock v-if="bloqueado" :size="13" class="ml-auto shrink-0" />
  </button>
</template>
